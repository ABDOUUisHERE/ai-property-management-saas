from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from typing import Any

from fastapi import APIRouter, FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic.json_schema import models_json_schema
from redis import Redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from starlette.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.core.context import SystemClock
from app.core.contracts import Health, Money, Pagination, Problem, StayDates, Timestamp
from app.core.database import SCHEMA_REVISION, UnitOfWork, make_engine
from app.core.errors import ApplicationError, install_error_handlers
from app.core.telemetry import RequestTelemetry, Telemetry, configure_logging
from app.modules.identity.provider import SupabaseProvider
from app.modules.identity.recovery import RecoveryService
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.router import identity_router, install_identity_errors
from app.modules.identity.security import AuthGuard, BrowserSecurity, RedisRateLimit
from app.modules.identity.sessions import SessionService
from app.modules.identity.transport import AuthEndpoint
from app.modules.identity.vault import TokenVault


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings if settings is not None else Settings()
    telemetry = Telemetry()
    if configuration.csrf_secret is None:
        raise ValueError("The API requires browser security configuration")
    csrf_key = configuration.csrf_secret.get_secret_value().encode("utf-8")
    security = BrowserSecurity(
        configuration.browser_origin, configuration.environment, csrf_key, SystemClock()
    )
    endpoint = AuthEndpoint(
        configuration.auth_url, configuration.auth_issuer, configuration.environment
    )
    vault = TokenVault(
        configuration.session_keys, active_key_id=configuration.session_active_key_id
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        engine = make_engine(configuration)
        app.state.engine = engine
        app.state.clock = SystemClock()
        app.state.unit_of_work = partial(UnitOfWork, sessionmaker(engine, expire_on_commit=False))
        provider = SupabaseProvider(endpoint)
        redis = Redis.from_url(
            configuration.broker_url(), socket_timeout=1, socket_connect_timeout=1
        )
        app.state.auth_provider = provider
        app.state.auth_security = security
        app.state.auth_limiter = RedisRateLimit(redis, csrf_key)
        app.state.auth_sessions = SessionService(
            IdentityRepository(sessionmaker(engine)), provider, vault, app.state.clock
        )
        app.state.auth_recovery = RecoveryService(
            IdentityRepository(sessionmaker(engine)),
            provider,
            app.state.clock,
            browser_origin=security.origin,
        )
        try:
            yield
        finally:
            provider.close()
            redis.close()
            engine.dispose()

    app = FastAPI(
        title="Property Management API",
        version="0.1.0",
        lifespan=lifespan,
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url=None,
    )
    app.add_middleware(AuthGuard)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[configuration.browser_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Organization-ID", "X-Request-ID"],
    )
    app.add_middleware(RequestTelemetry, telemetry=telemetry)
    install_error_handlers(app)
    install_identity_errors(app)
    app.include_router(identity_router())
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
        for path_url, path in schema["paths"].items():
            for method, operation in path.items():
                if method == "post":
                    parameters = operation.setdefault("parameters", [])
                    present = {parameter.get("name") for parameter in parameters}
                    for parameter in [
                        {
                            "in": "header",
                            "name": "Origin",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Configured browser origin",
                        },
                        {
                            "in": "header",
                            "name": "X-CSRF-Token",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "From GET /api/v1/auth/csrf",
                        },
                    ]:
                        if parameter["name"] not in present:
                            parameters.append(parameter)
                if path_url in {"/api/v1/me", "/api/v1/auth/refresh"}:
                    operation["security"] = [{"LocalSession": []}, {"SecureSession": []}]
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
        schema["components"]["securitySchemes"] = {
            "LocalSession": {
                "type": "apiKey",
                "in": "cookie",
                "name": "pms_session",
                "description": "Explicit local HTTP profile only",
            },
            "SecureSession": {
                "type": "apiKey",
                "in": "cookie",
                "name": "__Host-pms_session",
                "description": "HTTPS HttpOnly cookie",
            },
        }
        return schema

    app.openapi = openapi  # type: ignore[method-assign]
    return app
