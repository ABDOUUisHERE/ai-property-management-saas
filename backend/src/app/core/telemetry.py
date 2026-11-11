"""Allowlisted structured logs: no payload, query, token, URL or exception string."""

import json
import logging
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

from prometheus_client import CollectorRegistry, Counter, Histogram
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("pms.http")


class ResponseStreamError(RuntimeError):
    """Safe failure passed to the ASGI server after headers have been committed."""


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "service": "api",
                "action": "http_request",
                **getattr(record, "safe_fields", {}),
            },
            separators=(",", ":"),
        )


def configure_logging() -> None:
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


class Telemetry:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "pms_http_requests_total", "HTTP responses", ["route", "status"], registry=self.registry
        )
        self.duration = Histogram(
            "pms_http_request_seconds", "HTTP duration", ["route"], registry=self.registry
        )
        self.stream_failures = Counter(
            "pms_http_stream_failures_total",
            "Interrupted HTTP responses",
            ["route"],
            registry=self.registry,
        )


class RequestTelemetry:
    def __init__(self, app: ASGIApp, telemetry: Telemetry):
        self.app = app
        self.telemetry = telemetry

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        supplied = dict(scope.get("headers", [])).get(b"x-request-id", b"")
        try:
            request_id = str(UUID(supplied.decode("ascii")))
        except (ValueError, UnicodeError):
            request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started, status = time.monotonic(), 500
        response_started, stream_failed = False, False

        async def wrapped_send(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (b"x-request-id", request_id.encode()),
                ]
            await send(message)

        try:
            try:
                await self.app(scope, receive, wrapped_send)
            except Exception:
                if response_started:
                    # A second response start violates ASGI. Abort the stream with
                    # a safe exception; the server must not log the original error.
                    stream_failed = True
                    raise ResponseStreamError("Response stream failed") from None
                from starlette.requests import Request

                from app.core.errors import problem_response

                response = problem_response(
                    Request(scope), 500, "internal_error", "Unexpected error"
                )
                await response(scope, receive, wrapped_send)
        finally:
            route = getattr(scope.get("route"), "path", "unmatched")
            elapsed = time.monotonic() - started
            self.telemetry.requests.labels(route, str(status)).inc()
            self.telemetry.duration.labels(route).observe(elapsed)
            if stream_failed:
                self.telemetry.stream_failures.labels(route).inc()
            logger.info(
                "request",
                extra={
                    "safe_fields": {
                        "request_id": request_id,
                        "status": status,
                        "route": route,
                        "outcome": "interrupted" if stream_failed else "complete",
                        "duration_ms": round(elapsed * 1000, 2),
                    }
                },
            )
