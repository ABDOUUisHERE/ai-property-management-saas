import secrets
from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.bootstrap import create_app
from app.core.errors import ApplicationError
from app.modules.identity.contracts import (
    AuthenticationRejected,
    ProviderThrottled,
    ProviderUnavailable,
)
from app.modules.identity.repository import Profile
from app.modules.identity.security import BrowserSecurity
from app.modules.identity.sessions import NewSession, SessionExpired

ORIGIN = "http://127.0.0.1:18173"
CREDENTIALS = {"email": "fiction@example.test", "password": "fictional-password"}


class Limiter:
    def __init__(self):
        self.counts = Counter()
        self.down = False

    def check(self, bucket, subject, limit, window):
        if self.down:
            raise ApplicationError(503, "auth_unavailable", "Service unavailable")
        self.counts[bucket, subject] += 1
        if self.counts[bucket, subject] > limit:
            raise ApplicationError(429, "rate_limited", "Too many requests")


class Sessions:
    def __init__(self):
        self.profile = Profile(uuid4(), CREDENTIALS["email"])
        self.active = set()
        self.login_calls = 0
        self.refresh_calls = 0
        self.reject_login = False

    def login(self, email, password):
        self.login_calls += 1
        if self.reject_login:
            raise AuthenticationRejected()
        opaque = secrets.token_urlsafe(32)
        self.active.add(opaque)
        return NewSession(self.profile, datetime.now(UTC) + timedelta(hours=1), SecretStr(opaque))

    def resolve(self, opaque, *, force_refresh=False):
        if opaque.get_secret_value() not in self.active:
            raise SessionExpired()
        self.refresh_calls += int(force_refresh)
        return self.profile

    def logout(self, opaque):
        self.active.discard(opaque.get_secret_value())


class Signup:
    def __init__(self):
        self.failure = None
        self.calls = 0

    def register(self, email, password):
        self.calls += 1
        if self.failure:
            raise self.failure()


class Recovery:
    def __init__(self):
        self.requests, self.confirmations = [], []
        self.failure = None

    def request(self, email):
        self.requests.append(email)
        if self.failure:
            raise self.failure()

    def confirm(self, token_hash, password):
        self.confirmations.append((token_hash, password))
        if self.failure:
            raise self.failure()


@pytest.fixture
def browser(settings):
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        sessions, signup, limiter = Sessions(), Signup(), Limiter()
        app.state.auth_sessions = sessions
        app.state.auth_provider = signup
        app.state.auth_limiter = limiter
        app.state.auth_recovery = Recovery()
        yield client, sessions, signup, limiter


def headers(client, origin=ORIGIN):
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return {"Origin": origin, "X-CSRF-Token": response.json()["csrf_token"]}


@pytest.mark.parametrize(
    "path", ["register", "login", "logout", "refresh", "recovery/request", "recovery/confirm"]
)
def test_auth_mutations_require_origin_and_csrf_before_any_effect(browser, path):
    client, sessions, signup, limiter = browser
    url = f"/api/v1/auth/{path}"
    assert client.post(url, json=CREDENTIALS).status_code == 403
    assert client.post(url, json=CREDENTIALS, headers={"Origin": ORIGIN}).status_code == 403
    valid = headers(client)
    for origin in ("https://foreign.example.test", "null", ORIGIN + ".attacker.test"):
        response = client.post(url, json=CREDENTIALS, headers={**valid, "Origin": origin})
        assert response.status_code == 403
        assert response.json()["code"] == "origin_rejected"
        assert response.headers["cache-control"] == "no-store"
    assert sessions.login_calls == signup.calls == sessions.refresh_calls == 0
    assert limiter.counts["auth-ip", "testclient"] == 0


def test_recovery_request_is_generic_and_redirect_is_not_client_controlled(browser):
    client, _, _, _ = browser
    for email in ("known@example.test", "unknown@example.test"):
        response = client.post(
            "/api/v1/auth/recovery/request", json={"email": email}, headers=headers(client)
        )
        assert response.status_code == 202 and response.json() == {"status": "accepted"}
        assert response.headers["cache-control"] == "no-store"
    response = client.post(
        "/api/v1/auth/recovery/request",
        json={"email": CREDENTIALS["email"], "redirect_to": "https://foreign.example.test"},
        headers=headers(client),
    )
    assert response.status_code == 422 and "foreign" not in response.text
    assert len(client.app.state.auth_recovery.requests) == 2


def test_recovery_confirm_clears_cookies_and_never_creates_a_login(browser):
    client, sessions, _, _ = browser
    client.post("/api/v1/auth/login", json=CREDENTIALS, headers=headers(client))
    response = client.post(
        "/api/v1/auth/recovery/confirm",
        json={"token_hash": "a" * 56, "password": "new-fictional-password"},
        headers=headers(client),
    )
    assert response.status_code == 204 and response.content == b""
    assert not client.cookies.get("pms_session")
    assert not client.cookies.get("pms_csrf_context")
    assert sessions.login_calls == 1
    token, password = client.app.state.auth_recovery.confirmations[0]
    assert isinstance(token, SecretStr) and isinstance(password, SecretStr)


@pytest.mark.parametrize(
    "token,password,extra",
    [
        ("jwt-or-malformed", "new-fictional-password", {}),
        ("A" * 56, "new-fictional-password", {}),
        ("a" * 56, "short", {}),
        ("a" * 56, "new-fictional-password", {"type": "signup"}),
    ],
)
def test_recovery_refuses_malformed_weak_or_extra_input_without_reflection(
    browser, token, password, extra
):
    client, _, _, _ = browser
    response = client.post(
        "/api/v1/auth/recovery/confirm",
        json={"token_hash": token, "password": password, **extra},
        headers=headers(client),
    )
    assert response.status_code == 422
    assert token not in response.text and password not in response.text
    assert not client.app.state.auth_recovery.confirmations


@pytest.mark.parametrize(
    "failure,status", [(AuthenticationRejected, 401), (ProviderUnavailable, 503)]
)
def test_recovery_rejection_and_outage_are_sanitized(browser, failure, status):
    client, _, _, _ = browser
    client.app.state.auth_recovery.failure = failure
    response = client.post(
        "/api/v1/auth/recovery/confirm",
        json={"token_hash": "a" * 56, "password": "new-fictional-password"},
        headers=headers(client),
    )
    assert response.status_code == status
    assert "new-fictional" not in response.text and "a" * 56 not in response.text


def test_cookie_login_me_refresh_and_logout_without_tokens_in_json(browser):
    client, sessions, _, _ = browser
    anonymous = headers(client)
    response = client.post("/api/v1/auth/login", json=CREDENTIALS, headers=anonymous)
    assert response.status_code == 200
    opaque = client.cookies.get("pms_session")
    assert opaque and opaque not in response.text
    assert set(response.json()) == {"profile", "expires_at"}
    assert response.json()["profile"]["email"] == CREDENTIALS["email"]
    cookie = next(
        value
        for value in response.headers.get_list("set-cookie")
        if value.startswith("pms_session=")
    )
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    assert "Secure" not in cookie  # Explicit HTTP loopback profile only.
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/v1/me").status_code == 200
    assert client.post("/api/v1/auth/logout", headers=anonymous).status_code == 403
    authenticated = headers(client)
    assert client.post("/api/v1/auth/refresh", headers=authenticated).status_code == 200
    assert sessions.refresh_calls == 1
    assert client.post("/api/v1/auth/logout", headers=authenticated).status_code == 204
    assert opaque not in sessions.active
    assert client.get("/api/v1/me").status_code == 401
    assert not client.cookies.get("pms_session")


def test_csrf_token_cannot_move_to_another_cookie_context_or_cross_site_request(browser):
    client, sessions, _, _ = browser
    valid = headers(client)
    client.cookies.clear()
    headers(client)
    assert client.post("/api/v1/auth/login", json=CREDENTIALS, headers=valid).status_code == 403
    current = headers(client)
    assert (
        client.post(
            "/api/v1/auth/login",
            json=CREDENTIALS,
            headers={**current, "Sec-Fetch-Site": "cross-site"},
        ).status_code
        == 403
    )
    assert sessions.login_calls == 0


def test_corrupt_old_session_cookie_does_not_prevent_a_new_login(browser):
    client, _, _, _ = browser
    client.cookies.set("pms_session", "malformed", domain="127.0.0.1", path="/")
    response = client.post("/api/v1/auth/login", json=CREDENTIALS, headers=headers(client))
    assert response.status_code == 200
    assert client.get("/api/v1/me").status_code == 200


def test_login_replaces_and_revokes_the_previous_browser_session(browser):
    client, sessions, _, _ = browser
    client.post("/api/v1/auth/login", json=CREDENTIALS, headers=headers(client))
    old = client.cookies.get("pms_session")
    client.post("/api/v1/auth/login", json=CREDENTIALS, headers=headers(client))
    assert client.cookies.get("pms_session") != old
    assert old not in sessions.active
    assert len(sessions.active) == 1


def test_signup_rejections_are_non_enumerating_and_provider_outage_is_generic(browser):
    client, _, signup, _ = browser
    accepted = client.post("/api/v1/auth/register", json=CREDENTIALS, headers=headers(client))
    signup.failure = AuthenticationRejected
    rejected = client.post("/api/v1/auth/register", json=CREDENTIALS, headers=headers(client))
    assert accepted.status_code == rejected.status_code == 202
    assert accepted.json() == rejected.json() == {"status": "accepted"}
    signup.failure = ProviderThrottled
    throttled = client.post("/api/v1/auth/register", json=CREDENTIALS, headers=headers(client))
    assert throttled.status_code == 202 and throttled.json() == accepted.json()
    signup.failure = ProviderUnavailable
    unavailable = client.post("/api/v1/auth/register", json=CREDENTIALS, headers=headers(client))
    assert unavailable.status_code == 503 and unavailable.json()["code"] == "auth_unavailable"
    assert CREDENTIALS["email"] not in unavailable.text


def test_account_throttle_and_limiter_outage_prevent_authentication(browser):
    client, sessions, _, limiter = browser
    valid = headers(client)
    sessions.reject_login = True
    for _ in range(10):
        assert client.post("/api/v1/auth/login", json=CREDENTIALS, headers=valid).status_code == 401
    limited = client.post("/api/v1/auth/login", json=CREDENTIALS, headers=valid)
    assert limited.status_code == 429 and sessions.login_calls == 10
    limiter.down = True
    unavailable = client.post("/api/v1/auth/login", json=CREDENTIALS, headers=valid)
    assert unavailable.status_code == 503 and sessions.login_calls == 10


def test_source_throttle_cannot_be_bypassed_with_forwarded_headers(browser):
    client, sessions, _, _ = browser
    sessions.reject_login = True
    valid = headers(client)
    for index in range(30):
        response = client.post(
            "/api/v1/auth/login",
            json={**CREDENTIALS, "email": f"fiction-{index}@example.test"},
            headers={**valid, "X-Forwarded-For": f"192.0.2.{index}"},
        )
        assert response.status_code == 401
    limited = client.post("/api/v1/auth/login", json=CREDENTIALS, headers=valid)
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"


def test_cors_is_restricted_and_csrf_errors_are_readable_to_the_allowed_origin(browser):
    client, _, _, _ = browser
    for origin, status in ((ORIGIN, 200), ("https://foreign.example.test", 400)):
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,x-csrf-token",
            },
        )
        assert response.status_code == status
        assert response.headers.get("access-control-allow-origin") == (
            ORIGIN if status == 200 else None
        )
    response = client.post("/api/v1/auth/login", json=CREDENTIALS, headers={"Origin": ORIGIN})
    assert response.status_code == 403
    assert response.headers["access-control-allow-origin"] == ORIGIN


@pytest.mark.parametrize("streaming", [False, True])
def test_auth_body_is_bounded_before_credentials_are_processed(browser, streaming):
    client, sessions, _, _ = browser
    body = b'{"email":"fiction@example.test","password":"' + b"x" * 9000 + b'"}'
    response = client.post(
        "/api/v1/auth/login",
        headers={**headers(client), "Content-Type": "application/json"},
        content=(iter([body[:4000], body[4000:]]) if streaming else body),
    )
    assert response.status_code == 413
    assert sessions.login_calls == 0


def test_injected_fields_are_rejected_without_reflecting_passwords(browser):
    client, sessions, _, _ = browser
    response = client.post(
        "/api/v1/auth/login",
        headers=headers(client),
        json={**CREDENTIALS, "role": "owner", "organization_id": str(uuid4())},
    )
    assert response.status_code == 422
    assert CREDENTIALS["password"] not in response.text
    assert sessions.login_calls == 0


def test_global_guard_protects_future_business_mutations(browser):
    client, _, _, _ = browser
    effects = []

    @client.app.post("/api/v1/probe")
    def probe():
        effects.append(True)
        return {"status": "ok"}

    assert client.post("/api/v1/probe").status_code == 403
    assert effects == []
    assert client.post("/api/v1/probe", headers=headers(client)).status_code == 200
    assert effects == [True]


def test_https_deployment_uses_host_bound_secure_cookies(settings):
    origin = "https://app.example.test"
    configuration = settings.model_copy(
        update={
            "environment": "production",
            "browser_origin": origin,
            "auth_url": "https://auth.example.test",
            "auth_issuer": "https://auth.example.test",
        }
    )
    app = create_app(configuration)
    with TestClient(app, base_url=origin) as client:
        app.state.auth_limiter, app.state.auth_sessions = Limiter(), Sessions()
        token = headers(client, origin)
        response = client.post("/api/v1/auth/login", json=CREDENTIALS, headers=token)
        assert response.status_code == 200
        cookie = next(
            value
            for value in response.headers.get_list("set-cookie")
            if value.startswith("__Host-pms_session=")
        )
        assert "Secure" in cookie and "HttpOnly" in cookie and "Path=/" in cookie
        assert "Domain=" not in cookie
        assert client.get("/api/v1/me").status_code == 200


@pytest.mark.parametrize(
    "origin,environment",
    [
        (ORIGIN, "production"),
        ("http://remote.example.test", "local"),
        ("https://app.example.test/path", "production"),
        ("https://user:private@app.example.test", "production"),
    ],
)
def test_invalid_browser_origins_fail_closed(settings, origin, environment):
    with pytest.raises(ValueError):
        BrowserSecurity(origin, environment, b"x" * 64, datetime_clock())


def datetime_clock():
    class Clock:
        def now(self):
            return datetime.now(UTC)

    return Clock()


@pytest.mark.parametrize("offset", [3601, -6])
def test_csrf_expired_and_future_tokens_are_rejected(browser, offset):
    client, sessions, _, _ = browser

    class Clock:
        instant = datetime.now(UTC)

        def now(self):
            return self.instant

    clock = Clock()
    client.app.state.auth_security = BrowserSecurity(ORIGIN, "test", b"x" * 64, clock)
    valid = headers(client)
    clock.instant += timedelta(seconds=offset)
    assert client.post("/api/v1/auth/login", json=CREDENTIALS, headers=valid).status_code == 403
    assert sessions.login_calls == 0
