import pytest
from fastapi.testclient import TestClient

from app.bootstrap import create_app


@pytest.mark.parametrize("path", ["/api/v1/organizations", "/api/v1/organizations/current"])
def test_organization_reads_require_a_valid_session_before_tenant_resolution(settings, path):
    with TestClient(create_app(settings), base_url=settings.browser_origin) as client:
        response = client.get(
            path, headers={"X-Organization-ID": "00000000-0000-0000-0000-000000000001"}
        )
        assert response.status_code == 401
        assert response.json()["code"] == "session_expired"
        assert response.headers["cache-control"] == "no-store"


def test_organization_creation_rejects_origin_and_csrf_before_sql(settings):
    with TestClient(create_app(settings), base_url=settings.browser_origin) as client:
        response = client.post("/api/v1/organizations", json={"name": "Demo Atlas"})
        assert response.status_code == 403 and response.json()["code"] == "origin_rejected"


def test_organization_body_limit_is_applied_before_json_parsing_or_sql(settings):
    class Limiter:
        def check(self, *args):
            pass

    with TestClient(create_app(settings), base_url=settings.browser_origin) as client:
        client.app.state.auth_limiter = Limiter()
        token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/v1/organizations",
            content=b"x" * 8193,
            headers={
                "Origin": settings.browser_origin,
                "X-CSRF-Token": token,
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 413
        assert response.headers["cache-control"] == "no-store"
