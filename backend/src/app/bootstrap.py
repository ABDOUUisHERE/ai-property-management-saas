from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from typing import Any

from fastapi import APIRouter, FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic.json_schema import models_json_schema
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.context import SystemClock
from app.core.contracts import Health, Money, Pagination, Problem, StayDates, Timestamp
from app.core.database import SCHEMA_REVISION, UnitOfWork, make_engine
from app.core.errors import ApplicationError, install_error_handlers
from app.core.telemetry import RequestTelemetry, Telemetry, configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings if settings is not None else Settings()
    telemetry = Telemetry()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        engine = make_engine(configuration)
        app.state.engine = engine
        app.state.clock = SystemClock()
        app.state.unit_of_work = partial(UnitOfWork, sessionmaker(engine, expire_on_commit=False))
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="Property Management API",
        version="0.1.0",
        lifespan=lifespan,
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url=None,
    )
    app.add_middleware(RequestTelemetry, telemetry=telemetry)
    install_error_handlers(app)
    router = APIRouter()
    problems: dict[int | str, dict[str, Any]] = {
        code: {"model": Problem, "content": {"application/problem+json": {}}}
        for code in (422, 500, 503)
    }

    @router.get("/health/live", response_model=Health, responses=problems)
    def live() -> Health:
        return Health(status="ok")

    @router.get("/health/ready", response_model=Health, responses=problems)
    def ready(request: Request) -> Health:
        try:
            with request.app.state.engine.connect() as connection:
                revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
                if revision != SCHEMA_REVISION:
                    raise ApplicationError(503, "not_ready", "Service unavailable")
        except SQLAlchemyError:
            raise ApplicationError(503, "not_ready", "Service unavailable") from None
        return Health(status="ok")

    @router.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(telemetry.registry), media_type=CONTENT_TYPE_LATEST)

    app.include_router(router)
    original_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        schema = original_openapi()
        for path in schema["paths"].values():
            for operation in path.values():
                for response in operation.get("responses", {}).values():
                    content = response.get("content", {})
                    if "application/problem+json" in content:
                        response["content"] = {
                            "application/problem+json": {
                                "schema": {"$ref": "#/components/schemas/Problem"}
                            }
                        }
        _, contracts = models_json_schema(
            [(model, "validation") for model in (Pagination, Money, StayDates, Timestamp)],
            ref_template="#/components/schemas/{model}",
        )
        schema.setdefault("components", {}).setdefault("schemas", {}).update(contracts["$defs"])
        return schema

    app.openapi = openapi  # type: ignore[method-assign]
    return app
