import asyncio
import io
import logging
import traceback
from types import SimpleNamespace

from app.core.telemetry import JsonFormatter, RequestTelemetry, Telemetry, logger


def test_interrupted_response_has_one_header_block_and_no_sensitive_exception() -> None:
    messages = []
    telemetry = Telemetry()
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    previous_level = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    async def broken(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"partial", "more_body": True})
        raise RuntimeError("fixture-credential-must-stay-private")

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/download/private-id",
        "headers": [],
        "route": SimpleNamespace(path="/download/{identifier}"),
    }
    failure = None
    try:
        try:
            asyncio.run(RequestTelemetry(broken, telemetry)(scope, receive, send))
        except Exception as error:
            failure = error
        assert (
            len([message for message in messages if message["type"] == "http.response.start"]) == 1
        )
        assert isinstance(failure, RuntimeError)
        rendered = "".join(traceback.format_exception(failure))
        assert "fixture-credential-must-stay-private" not in rendered
        assert "fixture-credential-must-stay-private" not in output.getvalue()
        assert (
            telemetry.registry.get_sample_value(
                "pms_http_stream_failures_total", {"route": "/download/{identifier}"}
            )
            == 1
        )
        assert '"outcome":"interrupted"' in output.getvalue()
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
