import json
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import SecretStr

from app.modules.identity.contracts import (
    AuthenticationRejected,
    ProviderUnavailable,
    RefreshUncertain,
)
from app.modules.identity.provider import SupabaseProvider
from app.modules.identity.transport import AuthEndpoint


def account_payload(encode, claims):
    return {
        "access_token": encode(),
        "refresh_token": "private-refresh-token",
        "token_type": "bearer",
        "user": {
            "id": claims["sub"],
            "email": "fiction@example.test",
            "email_confirmed_at": "2026-11-11T00:00:00Z",
            "is_anonymous": False,
        },
    }


def test_signup_login_refresh_logout_contract(endpoint, public_key, encode, claims):
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("jwks.json"):
            return httpx.Response(200, json={"keys": [public_key]})
        if request.url.path == "/signup":
            return httpx.Response(200, json={"id": "not-for-the-browser", "identities": []})
        if request.url.path == "/logout":
            return httpx.Response(204)
        return httpx.Response(200, json=account_payload(encode, claims))

    provider = SupabaseProvider(endpoint, transport=httpx.MockTransport(handler))
    try:
        assert provider.register("fiction@example.test", SecretStr("private-password")) is None
        account = provider.login("fiction@example.test", SecretStr("private-password"))
        assert account.identity.subject == UUID(claims["sub"])
        assert account.email == "fiction@example.test"
        refreshed = provider.refresh(
            account.tokens.refresh_token,
            expected_subject=account.identity.subject,
            expected_session_id=account.identity.provider_session_id,
        )
        provider.logout(refreshed.tokens.access_token)
        assert requests[1].url.params["grant_type"] == "password"
        assert requests[-2].url.params["grant_type"] == "refresh_token"
        assert json.loads(requests[-2].content) == {"refresh_token": "private-refresh-token"}
        assert requests[-1].url.params["scope"] == "local"
        assert requests[-1].headers["authorization"].startswith("Bearer ")
        assert "private" not in repr(account)
        assert "private" not in repr(account.tokens)
        assert "fiction" not in repr(account)
    finally:
        provider.close()


def test_recovery_is_provider_typed_and_never_returns_tokens_to_requester(
    endpoint, public_key, encode, claims
):
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("jwks.json"):
            return httpx.Response(200, json={"keys": [public_key]})
        if request.url.path == "/recover":
            return httpx.Response(200, json={})
        if request.url.path == "/user":
            return httpx.Response(200, json={"id": claims["sub"]})
        return httpx.Response(200, json=account_payload(encode, claims))

    provider = SupabaseProvider(endpoint, transport=httpx.MockTransport(handler))
    try:
        redirect = "http://127.0.0.1:18173/auth/reset"
        assert provider.request_recovery("fiction@example.test", redirect_to=redirect) is None
        recovered = provider.verify_recovery(SecretStr("a" * 56))
        provider.change_recovered_password(recovered, SecretStr("private-new-password"))
        assert dict(requests[0].url.params) == {"redirect_to": redirect}
        assert json.loads(requests[0].content) == {"email": "fiction@example.test"}
        assert json.loads(requests[1].content) == {"type": "recovery", "token_hash": "a" * 56}
        assert requests[-1].method == "PUT" and requests[-1].url.path == "/user"
        assert json.loads(requests[-1].content) == {"password": "private-new-password"}
        assert requests[-1].headers["Authorization"] == (
            "Bearer " + recovered.tokens.access_token.get_secret_value()
        )
    finally:
        provider.close()


def test_password_update_rejects_a_foreign_provider_response(endpoint, public_key, encode, claims):
    def handler(request):
        if request.url.path.endswith("jwks.json"):
            return httpx.Response(200, json={"keys": [public_key]})
        if request.url.path == "/user":
            return httpx.Response(200, json={"id": str(uuid4())})
        return httpx.Response(200, json=account_payload(encode, claims))

    provider = SupabaseProvider(endpoint, transport=httpx.MockTransport(handler))
    try:
        account = provider.verify_recovery(SecretStr("a" * 56))
        with pytest.raises(ProviderUnavailable):
            provider.change_recovered_password(account, SecretStr("private-new-password"))
    finally:
        provider.close()


@pytest.mark.parametrize(
    "status,expected",
    [
        (400, AuthenticationRejected),
        (401, AuthenticationRejected),
        (403, AuthenticationRejected),
        (422, AuthenticationRejected),
        (429, ProviderUnavailable),
        (500, ProviderUnavailable),
        (302, ProviderUnavailable),
    ],
)
def test_upstream_errors_are_sanitized_and_not_retried(endpoint, status, expected):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status, text="private-password-refresh-and-email")

    provider = SupabaseProvider(endpoint, transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(expected) as error:
            provider.login("fiction@example.test", SecretStr("private-password"))
        assert "private" not in str(error.value)
        assert len(requests) == 1
    finally:
        provider.close()


@pytest.mark.parametrize("failure", ["timeout", "invalid-json", "oversized", "array"])
def test_transport_failure_is_bounded_and_safe(endpoint, failure):
    requests = []

    def handler(request):
        requests.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("private-password", request=request)
        if failure == "invalid-json":
            return httpx.Response(200, text="private-password")
        if failure == "oversized":
            return httpx.Response(200, text="x" * 65537)
        return httpx.Response(200, json=[])

    provider = SupabaseProvider(endpoint, transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ProviderUnavailable) as error:
            provider.login("fiction@example.test", SecretStr("private-password"))
        assert "private" not in str(error.value)
        assert len(requests) == 1
    finally:
        provider.close()


@pytest.mark.parametrize(
    "failure", ["foreign-subject", "unconfirmed", "anonymous", "missing-token"]
)
def test_unverified_or_foreign_response_cannot_create_identity(
    endpoint, public_key, encode, claims, failure
):
    payload = account_payload(encode, claims)
    if failure == "foreign-subject":
        payload["user"]["id"] = str(uuid4())
    elif failure == "unconfirmed":
        payload["user"]["email_confirmed_at"] = None
    elif failure == "anonymous":
        payload["user"]["is_anonymous"] = True
    else:
        payload.pop("refresh_token")

    def handler(request):
        return httpx.Response(
            200,
            json=({"keys": [public_key]} if request.url.path.endswith("jwks.json") else payload),
        )

    provider = SupabaseProvider(endpoint, transport=httpx.MockTransport(handler))
    try:
        with pytest.raises((AuthenticationRejected, ProviderUnavailable)):
            provider.login("fiction@example.test", SecretStr("private-password"))
    finally:
        provider.close()


@pytest.mark.parametrize(
    "failure", ["timeout", "server", "rejected", "malformed", "subject", "session"]
)
def test_refresh_ambiguity_never_retries_or_changes_identity(
    endpoint, public_key, encode, claims, failure
):
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("jwks.json"):
            return httpx.Response(200, json={"keys": [public_key]})
        if failure == "timeout":
            raise httpx.ReadTimeout("private-refresh-token", request=request)
        if failure in {"server", "rejected"}:
            return httpx.Response(500 if failure == "server" else 400)
        if failure == "malformed":
            return httpx.Response(200, json={"refresh_token": "already-rotated"})
        return httpx.Response(200, json=account_payload(encode, claims))

    provider = SupabaseProvider(endpoint, transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(RefreshUncertain) as error:
            provider.refresh(
                SecretStr("private-refresh-token"),
                expected_subject=uuid4() if failure == "subject" else UUID(claims["sub"]),
                expected_session_id=uuid4() if failure == "session" else UUID(claims["session_id"]),
            )
        assert "private" not in str(error.value)
        assert sum(request.url.path == "/token" for request in requests) == 1
    finally:
        provider.close()


@pytest.mark.parametrize(
    "url,issuer,environment",
    [
        ("http://127.0.0.1:19999", "http://127.0.0.1:19999", "production"),
        ("http://remote.example.test", "https://issuer.example.test", "local"),
        ("https://user:private@example.test", "https://issuer.example.test", "production"),
        ("https://auth.example.test?token=private", "https://issuer.example.test", "test"),
        ("https://auth.example.test/", "https://issuer.example.test", "test"),
    ],
)
def test_invalid_endpoint_configuration_fails_without_network(url, issuer, environment):
    with pytest.raises(ValueError) as error:
        AuthEndpoint(url, issuer, environment)
    assert "private" not in str(error.value)


def test_https_internal_transport_and_external_issuer_can_differ():
    endpoint = AuthEndpoint("http://auth:9999", "http://127.0.0.1:19999", "local")
    assert endpoint.url == "http://auth:9999"
    assert AuthEndpoint(
        "https://project.example.test/auth/v1", "https://project.example.test/auth/v1", "production"
    )


def test_slow_stream_stops_at_the_response_deadline(endpoint, monkeypatch):
    instant = [0]
    monkeypatch.setattr("app.modules.identity.transport.monotonic", lambda: instant[0])

    class SlowStream(httpx.SyncByteStream):
        closed = False

        def __iter__(self):
            yield b'{"'
            instant[0] = 9
            yield b'private-password":true}'
            pytest.fail("Slow provider stream was consumed beyond the deadline")

        def close(self):
            self.closed = True

    stream = SlowStream()
    provider = SupabaseProvider(
        endpoint, transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=stream))
    )
    try:
        with pytest.raises(ProviderUnavailable) as error:
            provider.login("fiction@example.test", SecretStr("private-password"))
        assert "private" not in str(error.value)
        assert stream.closed
    finally:
        provider.close()
