from uuid import UUID

import httpx
from pydantic import SecretStr

from app.modules.identity.contracts import (
    AuthenticatedAccount,
    AuthenticationRejected,
    ProviderTokens,
    ProviderUnavailable,
    RefreshUncertain,
    VerifiedIdentity,
)
from app.modules.identity.transport import AuthEndpoint, AuthTransport
from app.modules.identity.verification import AccessTokenVerifier


class SupabaseProvider:
    """Credential authority adapter; it never persists passwords or provider tokens."""

    def __init__(self, endpoint: AuthEndpoint, *, transport: httpx.BaseTransport | None = None):
        self._transport = AuthTransport(endpoint, transport=transport)
        self.verifier = AccessTokenVerifier(self._transport)

    def close(self) -> None:
        self._transport.close()

    def verify_access(self, access_token: SecretStr) -> VerifiedIdentity:
        return self.verifier.verify(access_token.get_secret_value())

    def register(self, email: str, password: SecretStr) -> None:
        # Do not return the upstream signup response, which may identify an account.
        self._transport.request(
            "POST", "/signup", payload={"email": email, "password": password.get_secret_value()}
        )

    def login(self, email: str, password: SecretStr) -> AuthenticatedAccount:
        payload = self._transport.request(
            "POST",
            "/token",
            params={"grant_type": "password"},
            payload={"email": email, "password": password.get_secret_value()},
        )
        return self._account(payload)

    def refresh(
        self, refresh_token: SecretStr, *, expected_subject: UUID, expected_session_id: UUID
    ) -> AuthenticatedAccount:
        try:
            payload = self._transport.request(
                "POST",
                "/token",
                params={"grant_type": "refresh_token"},
                payload={"refresh_token": refresh_token.get_secret_value()},
            )
            account = self._account(payload)
            if (
                account.identity.subject != expected_subject
                or account.identity.provider_session_id != expected_session_id
            ):
                raise RefreshUncertain()
            return account
        except (AuthenticationRejected, ProviderUnavailable):
            # Even a response-validation/JWKS failure can follow a successful remote
            # rotation. The service must revoke locally and require a new login.
            raise RefreshUncertain() from None

    def logout(self, access_token: SecretStr) -> None:
        self._transport.request(
            "POST",
            "/logout",
            params={"scope": "local"},
            bearer=access_token.get_secret_value(),
            empty=True,
        )

    def _account(self, payload: dict[str, object]) -> AuthenticatedAccount:
        access, refresh, user = (
            payload.get("access_token"),
            payload.get("refresh_token"),
            payload.get("user"),
        )
        if (
            not isinstance(access, str)
            or not 1 <= len(access) <= 16384
            or not isinstance(refresh, str)
            or not 1 <= len(refresh) <= 4096
            or payload.get("token_type") != "bearer"
            or not isinstance(user, dict)
        ):
            raise ProviderUnavailable()
        identity = self.verifier.verify(access)
        email, confirmed = user.get("email"), user.get("email_confirmed_at")
        if (
            user.get("id") != str(identity.subject)
            or not isinstance(email, str)
            or not 3 <= len(email) <= 320
            or not isinstance(confirmed, str)
            or not confirmed
            or user.get("is_anonymous", False) is not False
        ):
            raise AuthenticationRejected()
        return AuthenticatedAccount(
            identity, email, ProviderTokens(SecretStr(access), SecretStr(refresh))
        )
