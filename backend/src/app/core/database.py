from collections.abc import Callable
from types import TracebackType
from typing import Self

from sqlalchemy import Engine, MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings
from app.core.context import TenantContext

SCHEMA_REVISION = "0004_organizations"


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def make_engine(settings: Settings, *, dispatcher: bool = False) -> Engine:
    return create_engine(
        settings.database_url(dispatcher=dispatcher),
        pool_size=settings.pool_size,
        max_overflow=0,
        pool_timeout=settings.database_timeout_seconds,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={
            "connect_timeout": settings.database_timeout_seconds,
            "options": "-c statement_timeout=2000 -c lock_timeout=1000 "
            "-c idle_in_transaction_session_timeout=10000",
        },
    )


class UnitOfWork:
    """A transaction with a trusted tenant; explicit commit, rollback by default."""

    def __init__(self, sessions: sessionmaker[Session], context: TenantContext):
        if not isinstance(context, TenantContext):
            raise ValueError("A trusted tenant context is required")
        self._sessions = sessions
        self.context = context
        self.session: Session

    def __enter__(self) -> Self:
        self.session = self._sessions()
        try:
            self.session.begin()
            self.session.execute(
                text(
                    "SELECT set_config('app.organization_id', :tenant, true), "
                    "set_config('app.actor_id', :actor, true)"
                ),
                {"tenant": str(self.context.organization_id), "actor": str(self.context.actor_id)},
            )
        except BaseException:
            self.session.close()
            raise
        return self

    def commit(self) -> None:
        self.session.commit()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            self.session.rollback()
        finally:
            self.session.close()


UnitOfWorkFactory = Callable[[TenantContext], UnitOfWork]
