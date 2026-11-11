"""Revocable local sessions; provider calls never hold a SQL transaction open."""

import hashlib
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import SecretStr
from sqlalchemy.exc import SQLAlchemyError

from app.core.context import Clock
from app.modules.identity.contracts import (
    AuthenticatedAccount,
    AuthenticationRejected,
    ProviderUnavailable,
    RefreshUncertain,
    VerifiedIdentity,
)
from app.modules.identity.repository import IdentityRepository, Profile, StoredSession
from app.modules.identity.vault import InvalidTokenEnvelope, SessionBinding, TokenVault


class SessionExpired(Exception):
    def __init__(self) -> None:
        super().__init__("A new login is required")


class SessionBusy(Exception):
    def __init__(self) -> None:
        super().__init__("Session renewal is in progress")


class SessionAuthority(Protocol):
    def login(self, email: str, password: SecretStr) -> AuthenticatedAccount: ...

    def refresh(
        self, refresh_token: SecretStr, *, expected_subject: UUID, expected_session_id: UUID
    ) -> AuthenticatedAccount: ...

    def verify_access(self, access_token: SecretStr) -> VerifiedIdentity: ...

    def logout(self, access_token: SecretStr) -> None: ...


@dataclass(frozen=True)
class NewSession:
    profile: Profile
    expires_at: datetime
    opaque: SecretStr = field(repr=False)


def session_hash(opaque: SecretStr) -> str:
    raw = opaque.get_secret_value()
    if not re.fullmatch(r"[a-zA-Z0-9_-]{43}", raw):
        raise SessionExpired()
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


class SessionService:
    def __init__(
        self,
        repository: IdentityRepository,
        authority: SessionAuthority,
        vault: TokenVault,
        clock: Clock,
        *,
        lifetime: timedelta = timedelta(hours=24),
    ):
        if not timedelta(minutes=5) <= lifetime <= timedelta(days=7):
            raise ValueError("Session lifetime must be between five minutes and seven days")
        self._repository, self._authority, self._vault, self._clock = (
            repository,
            authority,
            vault,
            clock,
        )
        self._lifetime = lifetime
        self._refresh_margin = timedelta(seconds=30)

    def login(self, email: str, password: SecretStr) -> NewSession:
        # Capture before the network: a login begun before a recovery barrier
        # cannot create a valid local session after that recovery finishes.
        started_at = self._clock.now()
        account = self._authority.login(email, password)
        now, opaque = self._clock.now(), SecretStr(secrets.token_urlsafe(32))
        capability = session_hash(opaque)
        encrypted = self._vault.encrypt(
            account.tokens, SessionBinding(capability, account.identity.subject)
        )
        try:
            with self._repository.transaction(
                session_hash=capability, verified_subject=account.identity.subject
            ) as transaction:
                profile = transaction.upsert_profile(account.identity.subject, account.email, now)
                if transaction.profile(profile.id, session_started_at=started_at) is None:
                    raise SessionExpired()
                transaction.insert_session(
                    StoredSession(
                        capability,
                        profile.id,
                        account.identity.subject,
                        account.identity.provider_session_id,
                        encrypted,
                        account.identity.expires_at,
                        started_at,
                        started_at + self._lifetime,
                        0,
                        None,
                        None,
                        None,
                    )
                )
        except (SQLAlchemyError, SessionExpired):
            self._logout_provider(account.tokens.access_token)
            raise
        return NewSession(profile, started_at + self._lifetime, opaque)

    def resolve(self, opaque: SecretStr, *, force_refresh: bool = False) -> Profile:
        capability = session_hash(opaque)
        now, owner = self._clock.now(), uuid4()
        invalid, busy, renewing = False, False, False
        with self._repository.transaction(session_hash=capability) as transaction:
            record = transaction.lock_session(capability)
            if record is None or record.revoked_at is not None:
                invalid = True
            elif record.absolute_expires_at <= now or (
                record.refresh_deadline is not None and record.refresh_deadline <= now
            ):
                transaction.revoke(capability, now)
                invalid = True
            elif record.refresh_owner is not None:
                busy = True
            elif force_refresh or record.access_expires_at <= now + self._refresh_margin:
                transaction.claim_refresh(record, owner, now + self._refresh_margin)
                renewing = True
        if invalid or record is None:
            raise SessionExpired()
        if busy:
            raise SessionBusy()
        if renewing:
            return self._refresh(record, owner)
        try:
            tokens = self._vault.decrypt(record.encrypted_tokens or "", self._binding(record))
            identity = self._authority.verify_access(tokens.access_token)
            if (
                identity.subject != record.auth_subject
                or identity.provider_session_id != record.provider_session_id
                or identity.expires_at != record.access_expires_at
            ):
                raise AuthenticationRejected()
        except (AuthenticationRejected, InvalidTokenEnvelope):
            self._revoke(capability)
            raise SessionExpired() from None
        # Verification can fetch JWKS. Recheck local revocation/version afterwards.
        return self._current_profile(record)

    def logout(self, opaque: SecretStr) -> None:
        try:
            capability = session_hash(opaque)
        except SessionExpired:
            return
        with self._repository.transaction(session_hash=capability) as transaction:
            record = transaction.lock_session(capability)
            if record is None or record.revoked_at is not None:
                return
            transaction.revoke(capability, self._clock.now())
        try:
            tokens = self._vault.decrypt(record.encrypted_tokens or "", self._binding(record))
        except InvalidTokenEnvelope:
            return  # Local revocation is already committed, even after key loss.
        self._logout_provider(tokens.access_token)

    def _refresh(self, record: StoredSession, owner: UUID) -> Profile:
        account: AuthenticatedAccount | None = None
        try:
            tokens = self._vault.decrypt(record.encrypted_tokens or "", self._binding(record))
            account = self._authority.refresh(
                tokens.refresh_token,
                expected_subject=record.auth_subject,
                expected_session_id=record.provider_session_id,
            )
            if (
                account.identity.subject != record.auth_subject
                or account.identity.provider_session_id != record.provider_session_id
                or account.identity.expires_at <= self._clock.now() + self._refresh_margin
            ):
                raise AuthenticationRejected()
            encrypted = self._vault.encrypt(account.tokens, self._binding(record))
        except (
            RefreshUncertain,
            ProviderUnavailable,
            AuthenticationRejected,
            InvalidTokenEnvelope,
        ):
            self._revoke(record.session_hash)
            if account is not None:
                self._logout_provider(account.tokens.access_token)
            raise SessionExpired() from None
        completed, profile = False, None
        with self._repository.transaction(
            session_hash=record.session_hash, verified_subject=record.auth_subject
        ) as transaction:
            current = transaction.lock_session(record.session_hash)
            now = self._clock.now()
            if current is not None and current.revoked_at is None:
                if (
                    current.absolute_expires_at <= now
                    or current.refresh_deadline is None
                    or current.refresh_deadline <= now
                ):
                    transaction.revoke(record.session_hash, now)
                else:
                    completed = transaction.finish_refresh(
                        record, owner, encrypted, account.identity.expires_at
                    )
                    if completed:
                        transaction.upsert_profile(record.auth_subject, account.email, now)
                        profile = transaction.profile(
                            record.user_id, session_started_at=record.created_at
                        )
        if not completed or profile is None:
            self._logout_provider(account.tokens.access_token)
            raise SessionExpired()
        return profile

    def _current_profile(self, record: StoredSession) -> Profile:
        invalid, busy, profile = False, False, None
        with self._repository.transaction(session_hash=record.session_hash) as transaction:
            current = transaction.lock_session(record.session_hash)
            now = self._clock.now()
            if current is None or current.revoked_at is not None:
                invalid = True
            elif current.absolute_expires_at <= now:
                transaction.revoke(record.session_hash, now)
                invalid = True
            elif current.version != record.version or current.refresh_owner is not None:
                busy = True
            else:
                profile = transaction.profile(
                    current.user_id, session_started_at=current.created_at
                )
        if busy:
            raise SessionBusy()
        if invalid or profile is None:
            raise SessionExpired()
        return profile

    def _revoke(self, capability: str) -> None:
        with self._repository.transaction(session_hash=capability) as transaction:
            transaction.revoke(capability, self._clock.now())

    def _logout_provider(self, access_token: SecretStr) -> None:
        try:
            self._authority.logout(access_token)
        except (AuthenticationRejected, ProviderUnavailable):
            pass  # Best effort remotely; the local session is irrevocably closed.

    @staticmethod
    def _binding(record: StoredSession) -> SessionBinding:
        return SessionBinding(record.session_hash, record.auth_subject)
