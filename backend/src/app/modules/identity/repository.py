"""SQL for identity bootstrap and exact session capabilities, without tenant bypass."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class Profile:
    id: UUID
    email: str = field(repr=False)


@dataclass(frozen=True, repr=False)
class StoredSession:
    session_hash: str
    user_id: UUID
    auth_subject: UUID
    provider_session_id: UUID
    encrypted_tokens: str | None
    access_expires_at: datetime
    created_at: datetime
    absolute_expires_at: datetime
    version: int
    refresh_owner: UUID | None
    refresh_deadline: datetime | None
    revoked_at: datetime | None


class IdentityRepository:
    def __init__(self, sessions: sessionmaker[Session]):
        self._sessions = sessions

    @contextmanager
    def transaction(
        self, *, session_hash: str, verified_subject: UUID | None = None
    ) -> Iterator["IdentityTransaction"]:
        if not re.fullmatch(r"[a-f0-9]{64}", session_hash):
            raise ValueError("Invalid session capability")
        with self._sessions.begin() as session:
            session.execute(
                text(
                    "SELECT set_config('app.session_hash', :hash, true), "
                    "set_config('app.auth_subject', :subject, true)"
                ),
                {
                    "hash": session_hash,
                    "subject": str(verified_subject) if verified_subject else "",
                },
            )
            yield IdentityTransaction(session)


class IdentityTransaction:
    def __init__(self, session: Session):
        self._session = session

    def upsert_profile(self, subject: UUID, email: str, now: datetime) -> Profile:
        row = self._session.execute(
            text(
                "INSERT INTO users (id, auth_subject, email, created_at) "
                "VALUES (:id, :subject, :email, :now) ON CONFLICT (auth_subject) "
                "DO UPDATE SET email=EXCLUDED.email RETURNING id, email"
            ),
            {"id": uuid4(), "subject": subject, "email": email, "now": now},
        ).one()
        return Profile(row.id, row.email)

    def insert_session(self, record: StoredSession) -> None:
        self._session.execute(
            text(
                "INSERT INTO auth_sessions (session_hash, user_id, auth_subject, "
                "provider_session_id, encrypted_tokens, access_expires_at, created_at, "
                "absolute_expires_at) VALUES (:hash, :user, :subject, :provider_session, "
                ":tokens, :access_expiry, :created, :absolute_expiry)"
            ),
            {
                "hash": record.session_hash,
                "user": record.user_id,
                "subject": record.auth_subject,
                "provider_session": record.provider_session_id,
                "tokens": record.encrypted_tokens,
                "access_expiry": record.access_expires_at,
                "created": record.created_at,
                "absolute_expiry": record.absolute_expires_at,
            },
        )

    def lock_session(self, session_hash: str) -> StoredSession | None:
        row = (
            self._session.execute(
                text("SELECT * FROM auth_sessions WHERE session_hash=:hash FOR UPDATE"),
                {"hash": session_hash},
            )
            .mappings()
            .one_or_none()
        )
        return StoredSession(**row) if row else None

    def profile(
        self, user_id: UUID, *, session_started_at: datetime | None = None
    ) -> Profile | None:
        row = self._session.execute(
            text(
                "SELECT id, email FROM users WHERE id=:user AND recovery_owner IS NULL "
                "AND (cast(:started AS timestamptz) IS NULL OR sessions_valid_after IS NULL "
                "OR sessions_valid_after < cast(:started AS timestamptz))"
            ),
            {"user": user_id, "started": session_started_at},
        ).one_or_none()
        return Profile(row.id, row.email) if row else None

    def begin_recovery(self, subject: UUID, owner: UUID, now: datetime, deadline: datetime) -> bool:
        return (
            self._session.execute(
                text(
                    "UPDATE users SET sessions_valid_after=greatest(sessions_valid_after, :now), "
                    "recovery_owner=:owner, recovery_deadline=:deadline "
                    "WHERE auth_subject=:subject "
                    "AND (recovery_owner IS NULL OR recovery_deadline <= :now) RETURNING id"
                ),
                {"subject": subject, "owner": owner, "now": now, "deadline": deadline},
            ).scalar_one_or_none()
            is not None
        )

    def finish_recovery(self, subject: UUID, owner: UUID, now: datetime) -> bool:
        return (
            self._session.execute(
                text(
                    "UPDATE users SET recovery_owner=NULL, recovery_deadline=NULL "
                    "WHERE auth_subject=:subject AND recovery_owner=:owner "
                    "AND recovery_deadline > :now RETURNING id"
                ),
                {"subject": subject, "owner": owner, "now": now},
            ).scalar_one_or_none()
            is not None
        )

    def claim_refresh(self, record: StoredSession, owner: UUID, deadline: datetime) -> None:
        self._session.execute(
            text(
                "UPDATE auth_sessions SET refresh_owner=:owner, refresh_deadline=:deadline, "
                "version=version+1 WHERE session_hash=:hash"
            ),
            {"hash": record.session_hash, "owner": owner, "deadline": deadline},
        )

    def finish_refresh(
        self, record: StoredSession, owner: UUID, encrypted: str, access_expires: datetime
    ) -> bool:
        updated = self._session.execute(
            text(
                "UPDATE auth_sessions SET encrypted_tokens=:tokens, access_expires_at=:expiry, "
                "refresh_owner=NULL, refresh_deadline=NULL, version=version+1 "
                "WHERE session_hash=:hash AND version=:version AND refresh_owner=:owner "
                "AND revoked_at IS NULL RETURNING session_hash"
            ),
            {
                "tokens": encrypted,
                "expiry": access_expires,
                "hash": record.session_hash,
                "version": record.version + 1,
                "owner": owner,
            },
        ).scalar_one_or_none()
        return updated is not None

    def revoke(self, session_hash: str, now: datetime) -> None:
        self._session.execute(
            text(
                "UPDATE auth_sessions SET revoked_at=:now, encrypted_tokens=NULL, "
                "refresh_owner=NULL, refresh_deadline=NULL, version=version+1 "
                "WHERE session_hash=:hash AND revoked_at IS NULL"
            ),
            {"hash": session_hash, "now": now},
        )
