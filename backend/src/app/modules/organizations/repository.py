"""Actor-scoped SQL; creation and first owner share one transaction."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker


class Role(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    STAFF = "staff"


@dataclass(frozen=True)
class Organization:
    id: UUID
    name: str
    role: Role


class OrganizationRepository:
    def __init__(self, sessions: sessionmaker[Session]):
        self._sessions = sessions

    @contextmanager
    def transaction(
        self, actor_id: UUID, *, bootstrap_id: UUID | None = None
    ) -> Iterator["OrganizationTransaction"]:
        with self._sessions.begin() as session:
            session.execute(
                text(
                    "SELECT set_config('app.actor_id', :actor, true), "
                    "set_config('app.organization_id', '', true), "
                    "set_config('app.bootstrap_organization', :bootstrap, true)"
                ),
                {"actor": str(actor_id), "bootstrap": str(bootstrap_id) if bootstrap_id else ""},
            )
            yield OrganizationTransaction(session, actor_id)


class OrganizationTransaction:
    def __init__(self, session: Session, actor_id: UUID):
        self._session, self._actor = session, actor_id

    def create(self, organization_id: UUID, name: str, key: UUID, now: datetime) -> bool:
        return (
            self._session.execute(
                text(
                    "INSERT INTO organizations (id, name, created_by, creation_key, created_at) "
                    "VALUES (:id, :name, :actor, :key, :now) "
                    "ON CONFLICT (created_by, creation_key) DO NOTHING RETURNING id"
                ),
                {"id": organization_id, "name": name, "actor": self._actor, "key": key, "now": now},
            ).scalar_one_or_none()
            is not None
        )

    def first_owner(self, organization_id: UUID, now: datetime) -> None:
        self._session.execute(
            text(
                "INSERT INTO memberships (organization_id, user_id, role, active, created_at) "
                "VALUES (:organization, :actor, 'owner', true, :now)"
            ),
            {"organization": organization_id, "actor": self._actor, "now": now},
        )

    def created(self, key: UUID) -> Organization | None:
        row = self._session.execute(
            text(
                "SELECT o.id, o.name, m.role FROM organizations o JOIN memberships m "
                "ON m.organization_id=o.id WHERE o.created_by=:actor AND o.creation_key=:key "
                "AND m.user_id=:actor AND m.active"
            ),
            {"actor": self._actor, "key": key},
        ).one_or_none()
        return Organization(row.id, row.name, Role(row.role)) if row else None

    def list(self) -> list[Organization]:
        rows = self._session.execute(
            text(
                "SELECT o.id, o.name, m.role FROM organizations o JOIN memberships m "
                "ON m.organization_id=o.id WHERE m.user_id=:actor AND m.active ORDER BY o.id"
            ),
            {"actor": self._actor},
        ).all()
        return [Organization(row.id, row.name, Role(row.role)) for row in rows]

    def current(self, organization_id: UUID) -> Organization | None:
        row = self._session.execute(
            text(
                "SELECT o.id, o.name, m.role FROM organizations o JOIN memberships m "
                "ON m.organization_id=o.id WHERE o.id=:organization "
                "AND m.user_id=:actor AND m.active"
            ),
            {"organization": organization_id, "actor": self._actor},
        ).one_or_none()
        return Organization(row.id, row.name, Role(row.role)) if row else None
