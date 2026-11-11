"""Exercise the production adapter against local Auth and a real Mailpit email."""

import html
import os
import re
import secrets
import time
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import SecretStr

from app.modules.identity.contracts import AuthenticationRejected, RefreshUncertain
from app.modules.identity.provider import SupabaseProvider
from app.modules.identity.transport import AuthEndpoint

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


def test_real_email_login_refresh_and_provider_logout():
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
            assert provider.register(email, password) is None
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
