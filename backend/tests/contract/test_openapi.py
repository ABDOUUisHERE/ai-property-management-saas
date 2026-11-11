import json
from copy import deepcopy
from pathlib import Path

from openapi_spec_validator import validate

from app.bootstrap import create_app
from app.core.config import Settings


def test_openapi_matches_reviewed_snapshot(settings: Settings) -> None:
    app = create_app(settings)
    schema = deepcopy(app.openapi())
    assert app.openapi() == schema  # Repeated serving must not duplicate CSRF headers.
    validate(schema)
    target = Path(__file__).resolve().parents[3] / "docs/api/openapi.json"
    assert schema == json.loads(target.read_text(encoding="utf-8"))
    assert set(schema["paths"]) == {
        "/health/live",
        "/health/ready",
        "/api/v1/auth/csrf",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/recovery/request",
        "/api/v1/auth/recovery/confirm",
        "/api/v1/organizations",
        "/api/v1/organizations/current",
        "/api/v1/me",
    }
    assert set(schema["components"]["schemas"]["SessionResponse"]["properties"]) == {
        "profile",
        "expires_at",
    }
    login = schema["paths"]["/api/v1/auth/login"]["post"]
    assert {parameter["name"] for parameter in login["parameters"]} == {"Origin", "X-CSRF-Token"}
    assert schema["paths"]["/api/v1/me"]["get"]["security"] == [
        {"LocalSession": []},
        {"SecureSession": []},
    ]
    assert {"Problem", "Money", "Pagination", "StayDates", "Timestamp"} <= set(
        schema["components"]["schemas"]
    )
