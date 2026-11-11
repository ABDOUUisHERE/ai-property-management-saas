from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from pydantic import SecretStr


class AuthenticationRejected(Exception):
    def __init__(self) -> None:
        super().__init__("Authentication rejected")


class ProviderUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("Authentication provider unavailable")


class RefreshUncertain(Exception):
    """A refresh may have rotated remotely; revoke locally instead of retrying it."""

    def __init__(self) -> None:
        super().__init__("Refresh outcome uncertain; a new login is required")


@dataclass(frozen=True)
class VerifiedIdentity:
    subject: UUID
    provider_session_id: UUID
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class ProviderTokens:
    access_token: SecretStr = field(repr=False)
    refresh_token: SecretStr = field(repr=False)


@dataclass(frozen=True)
class AuthenticatedAccount:
    identity: VerifiedIdentity
    email: str = field(repr=False)
    tokens: ProviderTokens = field(repr=False)
