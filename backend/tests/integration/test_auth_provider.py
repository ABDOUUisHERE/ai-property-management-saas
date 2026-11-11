"""Exercise the production adapter against local Auth and a real Mailpit email."""

import base64
import html
import os
import re
import secrets
import shutil
import subprocess
import time
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from pydantic import SecretStr
from sqlalchemy.orm import sessionmaker

from app.bootstrap import create_app
from app.core.context import SystemClock
from app.modules.identity.contracts import AuthenticationRejected, RefreshUncertain
from app.modules.identity.provider import SupabaseProvider
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.sessions import SessionExpired, SessionService
from app.modules.identity.transport import AuthEndpoint
from app.modules.identity.vault import TokenVault

pytestmark = pytest.mark.integration


def confirmation_link(client: httpx.Client, mail_url: str, email: str, auth_url: str) -> str:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        response = client.get(f"{mail_url}/api/v1/search", params={"query": f"to:{email}"})
        assert response.status_code == 200
        for message in response.json().get("messages", []):
            detail = client.get(f"{mail_url}/api/v1/message/{message['ID']}")
            assert detail.status_code == 200
            body = detail.json()
            text = html.unescape(body.get("Text", "") + body.get("HTML", ""))
            for link in re.findall(r"https?://[^\s<>\"']+", text):
                parsed = urlsplit(link)
                if f"{parsed.scheme}://{parsed.netloc}" == auth_url and parsed.path == "/verify":
                    return link
        time.sleep(0.25)
    pytest.fail("Confirmation email not received in local Mailpit")


def test_real_email_login_refresh_and_provider_logout(engine, database):
    if os.environ.get("PMS_INTEGRATION") != "1":
        pytest.skip("Use scripts/application.py test for the isolated local Auth stack")
    auth_url, mail_url = os.environ["PMS_TEST_AUTH_URL"], os.environ["PMS_TEST_MAIL_URL"]
    # Never point a fixture with administration capabilities at an external service.
    for url in (auth_url, mail_url):
        assert urlsplit(url).scheme == "http" and urlsplit(url).hostname == "127.0.0.1"
    email = f"p03-{uuid4().hex}@example.test"
    password = SecretStr(secrets.token_urlsafe(32))
    provider = SupabaseProvider(AuthEndpoint(auth_url, auth_url, "test"))
    headers = {"Authorization": f"Bearer {os.environ['PMS_TEST_AUTH_ADMIN_TOKEN']}"}
    with httpx.Client(timeout=5, follow_redirects=False, trust_env=False) as client:
        try:
            with TestClient(create_app(database), base_url=database.browser_origin) as browser:
                token_response = browser.get("/api/v1/auth/csrf")
                assert token_response.status_code == 200
                registered = browser.post(
                    "/api/v1/auth/register",
                    json={
                        "email": email,
                        "password": password.get_secret_value(),
                    },
                    headers={
                        "Origin": database.browser_origin,
                        "X-CSRF-Token": token_response.json()["csrf_token"],
                    },
                )
                assert registered.status_code == 202 and registered.json() == {"status": "accepted"}
            with pytest.raises(AuthenticationRejected):
                provider.login(email, password)
            link = confirmation_link(client, mail_url, email, auth_url)
            assert client.get(link).status_code in {302, 303}
            account = provider.login(email, password)
            assert account.email == email
            refreshed = provider.refresh(
                account.tokens.refresh_token,
                expected_subject=account.identity.subject,
                expected_session_id=account.identity.provider_session_id,
            )
            assert refreshed.identity.subject == account.identity.subject
            provider.logout(refreshed.tokens.access_token)
            with pytest.raises(RefreshUncertain):
                provider.refresh(
                    refreshed.tokens.refresh_token,
                    expected_subject=account.identity.subject,
                    expected_session_id=account.identity.provider_session_id,
                )
            vault = TokenVault(
                {"test": SecretStr(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())},
                active_key_id="test",
            )
            service = SessionService(
                IdentityRepository(sessionmaker(engine)), provider, vault, SystemClock()
            )
            local = service.login(email, password)
            repeated = service.login(email, password)
            assert local.profile.id == repeated.profile.id
            assert service.resolve(local.opaque).email == email
            assert service.resolve(local.opaque, force_refresh=True) == local.profile
            service.logout(local.opaque)
            with pytest.raises(SessionExpired):
                service.resolve(local.opaque)
            # Logging out one provider session must preserve a second login.
            assert service.resolve(repeated.opaque) == repeated.profile
            service.logout(repeated.opaque)
            with TestClient(create_app(database), base_url=database.browser_origin) as browser:
                token_response = browser.get("/api/v1/auth/csrf")
                signed_headers = {
                    "Origin": database.browser_origin,
                    "X-CSRF-Token": token_response.json()["csrf_token"],
                }
                logged_in = browser.post(
                    "/api/v1/auth/login",
                    json={
                        "email": email,
                        "password": password.get_secret_value(),
                    },
                    headers=signed_headers,
                )
                assert logged_in.status_code == 200
                assert set(logged_in.json()) == {"profile", "expires_at"}
                assert logged_in.json()["profile"]["id"] == str(local.profile.id)
                opaque = browser.cookies.get("pms_session")
                assert opaque and opaque not in logged_in.text
                me = browser.get("/api/v1/me")
                assert me.status_code == 200 and me.json()["email"] == email
                token_response = browser.get("/api/v1/auth/csrf")
                signed_headers["X-CSRF-Token"] = token_response.json()["csrf_token"]
                renewed = browser.post("/api/v1/auth/refresh", headers=signed_headers)
                assert renewed.status_code == 200
                organization = browser.post(
                    "/api/v1/organizations",
                    json={"name": "Demo Atlas", "request_id": str(uuid4())},
                    headers=signed_headers,
                )
                assert organization.status_code == 201
                assert organization.json()["role"] == "owner"
                organization_id = organization.json()["id"]
                selected = browser.get(
                    "/api/v1/organizations/current", headers={"X-Organization-ID": organization_id}
                )
                assert selected.status_code == 200 and selected.json() == organization.json()
                logged_out = browser.post("/api/v1/auth/logout", headers=signed_headers)
                assert logged_out.status_code == 204
                rejected = browser.get("/api/v1/me", headers={"Cookie": f"pms_session={opaque}"})
                assert rejected.status_code == 401
            # Request/confirm recovery through the real HTTP facade and Mailpit.
            # Keep two old local sessions to prove immediate revocation even
            # though their provider access JWTs have not reached expiry.
            old = service.login(email, password)
            other_old = service.login(email, password)
            new_password = SecretStr(secrets.token_urlsafe(32))
            with TestClient(create_app(database), base_url=database.browser_origin) as browser:

                def signed():
                    csrf = browser.get("/api/v1/auth/csrf")
                    assert csrf.status_code == 200
                    return {
                        "Origin": database.browser_origin,
                        "X-CSRF-Token": csrf.json()["csrf_token"],
                    }

                def request_reset(address):
                    response = browser.post(
                        "/api/v1/auth/recovery/request", json={"email": address}, headers=signed()
                    )
                    assert response.status_code == 202
                    assert response.json() == {"status": "accepted"}

                request_reset(f"unknown-{uuid4().hex}@example.test")
                request_reset(email)
                token = recovery_token(client, mail_url, email, database.browser_origin)
                body = {"token_hash": token, "password": new_password.get_secret_value()}
                reset = browser.post("/api/v1/auth/recovery/confirm", json=body, headers=signed())
                assert reset.status_code == 204
                assert not browser.cookies.get("pms_session")
                assert (
                    browser.post(
                        "/api/v1/auth/recovery/confirm", json=body, headers=signed()
                    ).status_code
                    == 401
                )
                for session in (old, other_old):
                    with pytest.raises(SessionExpired):
                        service.resolve(session.opaque)
                    denied = browser.get(
                        "/api/v1/organizations/current",
                        headers={
                            "Cookie": f"pms_session={session.opaque.get_secret_value()}",
                            "X-Organization-ID": organization_id,
                        },
                    )
                    assert denied.status_code == 401
                with pytest.raises(AuthenticationRejected):
                    provider.login(email, password)
                renewed_local = service.login(email, new_password)
                assert service.resolve(renewed_local.opaque) == old.profile
                service.logout(renewed_local.opaque)
                # Expire only this fixture's recovery timestamp in the local
                # provider DB. No credentials or email payload enter shell code.
                # This tests GoTrue's real expiry check without waiting an hour.
                time.sleep(1.1)  # Provider's configured email resend interval.
                request_reset(email)
                expired = recovery_token(
                    client, mail_url, email, database.browser_origin, previous=token
                )
                expire_fixture_recovery(account.identity.subject)
                assert (
                    browser.post(
                        "/api/v1/auth/recovery/confirm",
                        json={"token_hash": expired, "password": password.get_secret_value()},
                        headers=signed(),
                    ).status_code
                    == 401
                )
                valid_after_expired = service.login(email, new_password)
                service.logout(valid_after_expired.opaque)
        finally:
            provider.close()
            # The public adapter deliberately hides signup account identifiers.
            # Cleanup locates only this exact random fictional address, even when
            # the test failed before login, and never removes other users.
            response = client.get(
                f"{auth_url}/admin/users",
                params={"filter": email, "per_page": 1000},
                headers=headers,
            )
            assert response.status_code == 200
            for user in response.json()["users"]:
                if user.get("email") == email:
                    identifier = UUID(user["id"])
                    deleted = client.delete(f"{auth_url}/admin/users/{identifier}", headers=headers)
                    assert deleted.status_code in {200, 204}


def recovery_token(client, mail_url, email, origin, *, previous=None):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        response = client.get(f"{mail_url}/api/v1/search", params={"query": f"to:{email}"})
        assert response.status_code == 200
        for message in response.json().get("messages", []):
            detail = client.get(f"{mail_url}/api/v1/message/{message['ID']}")
            assert detail.status_code == 200
            body = detail.json()
            text = html.unescape(body.get("Text", "") + body.get("HTML", ""))
            for link in re.findall(r"https?://[^\s<>\"']+", text):
                parsed = urlsplit(link)
                if f"{parsed.scheme}://{parsed.netloc}" == origin and parsed.path == "/auth/reset":
                    assert not parsed.query  # No secret in server/proxy request logs.
                    token = parse_qs(parsed.fragment).get("token_hash", [""])[0]
                    assert re.fullmatch(r"[a-f0-9]{56}", token)
                    if token != previous:
                        return token
        time.sleep(0.25)
    pytest.fail("Recovery email with the configured safe fragment link not received")


def expire_fixture_recovery(subject):
    assert isinstance(subject, UUID)
    project = os.environ["PMS_COMPOSE_PROJECT"]
    assert re.fullmatch(r"[a-z0-9][a-z0-9_-]*", project)
    docker = shutil.which("docker")
    assert docker
    query = (
        sql.SQL(
            "UPDATE auth.users SET recovery_sent_at=now()-interval '2 hours' "
            "WHERE id={} AND email LIKE 'p03-%@example.test' RETURNING id;"
        )
        .format(sql.Literal(subject))
        .as_string()
    )
    result = subprocess.run(  # noqa: S603 - fixed command, validated project/UUID, no shell
        [
            docker,
            "exec",
            f"{project}-auth-db-1",
            "psql",
            "-X",
            "-U",
            "auth_bootstrap",
            "-d",
            "auth",
            "-v",
            "ON_ERROR_STOP=1",
            "-Atc",
            query,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, "Fixture-only provider expiry update failed; output withheld"
    assert result.stdout.splitlines() == [str(subject), "UPDATE 1"]
