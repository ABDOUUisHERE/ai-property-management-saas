import json
from pathlib import Path

from openapi_spec_validator import validate

from app.bootstrap import create_app
from app.core.config import Settings


def test_openapi_matches_reviewed_snapshot(settings: Settings) -> None:
    schema = create_app(settings).openapi()
    validate(schema)
    target = Path(__file__).resolve().parents[3] / "docs/api/openapi.json"
    assert schema == json.loads(target.read_text(encoding="utf-8"))
    assert set(schema["paths"]) == {"/health/live", "/health/ready"}
    assert {"Problem", "Money", "Pagination", "StayDates", "Timestamp"} <= set(
        schema["components"]["schemas"]
    )
