import io
import logging
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.bootstrap import create_app
from app.core.config import Settings
from app.core.contracts import Money, Pagination, StayDates, Timestamp
from app.core.telemetry import JsonFormatter, logger


def test_configuration_rejects_missing_or_weak_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PMS_DATABASE_PASSWORD", raising=False)
    with pytest.raises(ValidationError):
        Settings()
    with pytest.raises(ValidationError) as error:
        Settings(database_password="secret", redis_password="b" * 48)
    assert "input_value" not in str(error.value)


def test_live_ready_and_shutdown(settings: Settings) -> None:
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        response = client.get("/health/ready", headers={"X-Request-ID": "untrusted"})
        assert response.status_code == 503
        assert UUID(response.headers["x-request-id"])
        assert response.json()["code"] == "not_ready"
        assert "password" not in response.text
        assert client.get("/health/live").status_code == 200
        assert "pms_http_requests_total" in client.get("/metrics").text
    assert app.state.engine.pool.checkedout() == 0


def test_errors_and_logs_do_not_reflect_input(settings: Settings) -> None:
    app = create_app(settings)
    secret = "private-guest-password-and-token"

    @app.get("/explode")
    def explode() -> None:
        raise RuntimeError(secret)

    @app.get("/validate")
    def validate(number: int) -> dict[str, int]:
        return {"number": number}

    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    try:
        with TestClient(app) as client:
            for path, expected in (
                ("/explode", 500),
                (f"/validate?number={secret}", 422),
                (f"/missing/{secret}", 404),
            ):
                response = client.get(
                    path, headers={"Authorization": secret, "X-Request-ID": secret}
                )
                assert response.status_code == expected
                assert response.headers["content-type"] == "application/problem+json"
                assert response.json()["request_id"] == response.headers["x-request-id"]
                assert secret not in response.text
        assert secret not in output.getvalue()
        assert "traceback" not in output.getvalue().lower()
    finally:
        logger.removeHandler(handler)


@pytest.mark.parametrize(
    "model,values",
    [
        (Money, {"amount_minor": 1.5, "currency": "MAD"}),
        (Money, {"amount_minor": 5, "currency": "mad"}),
        (Pagination, {"limit": 101}),
        (StayDates, {"check_in": "2026-11-10", "check_out": "2026-11-10"}),
        (Timestamp, {"occurred_at": "2026-11-10T12:00:00"}),
    ],
)
def test_contract_boundaries(model: type, values: dict) -> None:
    with pytest.raises(ValidationError):
        model(**values)
