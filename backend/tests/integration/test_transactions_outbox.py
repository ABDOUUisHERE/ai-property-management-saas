from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from app.bootstrap import create_app
from app.core.config import Settings
from app.core.context import SystemClock, TenantContext
from app.core.database import UnitOfWork, make_engine
from app.workers.outbox import consume, dispatch_batch, enqueue

pytestmark = pytest.mark.integration


def context() -> TenantContext:
    return TenantContext(uuid4(), uuid4())


def test_real_role_readiness_and_isolation(engine: Engine, database: Settings) -> None:
    from fastapi.testclient import TestClient

    with TestClient(create_app(database)) as client:
        assert client.get("/health/ready").status_code == 200
    with engine.connect() as connection:
        role = connection.execute(
            text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user")
        ).one()
        assert role == (False, False)
        assert connection.scalar(text("SELECT count(*) FROM outbox_events")) == 0
    sessions = sessionmaker(engine)
    a, b = context(), context()
    with UnitOfWork(sessions, a) as uow:
        enqueue(
            uow,
            event_type="system.probe",
            payload={"test": True},
            consumer="system.probe",
            clock=SystemClock(),
        )
        uow.commit()
    with UnitOfWork(sessions, b) as uow:
        assert uow.session.scalar(text("SELECT count(*) FROM outbox_events")) == 0
        with pytest.raises(DBAPIError):
            uow.session.execute(
                text("INSERT INTO outbox_events VALUES (:id, :tenant, 'x', '{}', now())"),
                {"id": uuid4(), "tenant": a.organization_id},
            )
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT nullif(current_setting('app.organization_id', true), '')")
            )
            is None
        )
        assert connection.scalar(text("SELECT count(*) FROM outbox_events")) == 0
        with pytest.raises(DBAPIError):
            connection.execute(text("CREATE TABLE forbidden (id int)"))


def test_rollback_and_reused_pool(engine: Engine) -> None:
    sessions, a = sessionmaker(engine), context()
    with pytest.raises(ValueError):
        UnitOfWork(sessions, None)  # type: ignore[arg-type]
    with UnitOfWork(sessions, a) as uow:
        enqueue(
            uow, event_type="system.probe", payload={}, consumer="system.probe", clock=SystemClock()
        )
    with UnitOfWork(sessions, a) as uow:
        assert uow.session.scalar(text("SELECT count(*) FROM outbox_events")) == 0
    with pytest.raises(RuntimeError), UnitOfWork(sessions, a) as uow:
        enqueue(
            uow, event_type="system.probe", payload={}, consumer="system.probe", clock=SystemClock()
        )
        raise RuntimeError("rollback")
    with UnitOfWork(sessions, a) as uow:
        assert uow.session.scalar(text("SELECT count(*) FROM outbox_events")) == 0
    assert engine.pool.checkedout() == 0


def test_durable_redelivery_crash_and_idempotent_effect(engine: Engine, database: Settings) -> None:
    sessions, a, clock = sessionmaker(engine), context(), SystemClock()
    with UnitOfWork(sessions, a) as uow:
        identifier = enqueue(
            uow, event_type="system.probe", payload={}, consumer="system.probe", clock=clock
        )
        uow.commit()
    dispatcher = make_engine(database, dispatcher=True)
    now, messages = clock.now() + timedelta(seconds=1), []
    try:
        with dispatcher.connect() as connection, pytest.raises(DBAPIError):
            connection.execute(text("SELECT * FROM outbox_events"))

        def lost(tenant: str, event: str, consumer: str) -> None:
            raise ConnectionError("broker unavailable after lease commit")

        with pytest.raises(ConnectionError):
            dispatch_batch(dispatcher, lost, now=now)
        dispatch_batch(
            dispatcher, lambda *args: messages.append(args), now=now + timedelta(seconds=31)
        )
        assert any(message[1] == str(identifier) for message in messages)

        def failed_effect(session: Session, tenant: TenantContext, payload: dict) -> None:
            # An effect and its receipt must both roll back when the process fails.
            session.execute(
                text("UPDATE outbox_deliveries SET error_code='effect' WHERE event_id=:id"),
                {"id": identifier},
            )
            raise RuntimeError("consumer crashed")

        with pytest.raises(RuntimeError):
            consume(sessions, a, identifier, "system.probe", failed_effect, clock)

        def effect(session: Session, tenant: TenantContext, payload: dict) -> None:
            session.execute(
                text("UPDATE outbox_deliveries SET error_code='effect' WHERE event_id=:id"),
                {"id": identifier},
            )

        assert consume(sessions, a, identifier, "system.probe", effect, clock)
        assert not consume(sessions, a, identifier, "system.probe", effect, clock)
        assert not consume(sessions, context(), identifier, "system.probe", effect, clock)
        with UnitOfWork(sessions, a) as uow:
            assert (
                uow.session.scalar(
                    text("SELECT count(*) FROM consumer_receipts WHERE event_id=:id"),
                    {"id": identifier},
                )
                == 1
            )
    finally:
        dispatcher.dispose()
