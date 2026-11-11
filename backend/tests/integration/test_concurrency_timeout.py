import threading
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.context import SystemClock, TenantContext
from app.core.database import UnitOfWork, make_engine
from app.workers.outbox import consume, enqueue

pytestmark = pytest.mark.integration


def test_two_consumers_commit_one_effect(database: Settings) -> None:
    engine = make_engine(database.model_copy(update={"pool_size": 2}))
    sessions, clock = sessionmaker(engine), SystemClock()
    context = TenantContext(uuid4(), uuid4(), principal="system")
    try:
        with UnitOfWork(sessions, context) as uow:
            identifier = enqueue(
                uow, event_type="system.probe", payload={}, consumer="system.probe", clock=clock
            )
            uow.commit()
        start = threading.Barrier(2)

        def handler(session: Session, tenant: TenantContext, payload: dict) -> None:
            session.execute(
                text("UPDATE outbox_deliveries SET attempts=attempts+1 WHERE event_id=:id"),
                {"id": identifier},
            )

        def run() -> bool:
            start.wait(timeout=5)
            return consume(sessions, context, identifier, "system.probe", handler, clock)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: run(), range(2)))
        assert sorted(results) == [False, True]
        with UnitOfWork(sessions, context) as uow:
            assert (
                uow.session.scalar(
                    text("SELECT attempts FROM outbox_deliveries WHERE event_id=:id"),
                    {"id": identifier},
                )
                == 1
            )
            assert (
                uow.session.scalar(
                    text("SELECT count(*) FROM consumer_receipts WHERE event_id=:id"),
                    {"id": identifier},
                )
                == 1
            )
    finally:
        engine.dispose()


def test_sql_timeout_is_bounded_and_connection_recovers(engine: Engine) -> None:
    started = time.monotonic()
    with engine.connect() as connection:
        with pytest.raises(DBAPIError):
            connection.execute(text("SELECT pg_sleep(5)"))
        connection.rollback()
        assert connection.scalar(text("SELECT 1")) == 1
    assert time.monotonic() - started < 4.5
