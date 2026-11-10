import json
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.context import Clock, TenantContext
from app.core.database import UnitOfWork

Handler = Callable[[Session, TenantContext, dict[str, Any]], None]
Publisher = Callable[[str, str, str], None]


def enqueue(
    uow: UnitOfWork,
    *,
    event_type: str,
    payload: dict[str, Any],
    consumer: str,
    clock: Clock,
) -> UUID:
    """The caller commits business changes and this event together."""
    identifier = uuid4()
    parameters = {
        "id": identifier,
        "tenant": uow.context.organization_id,
        "type": event_type,
        "payload": json.dumps(payload),
        "now": clock.now(),
        "consumer": consumer,
    }
    uow.session.execute(
        text(
            "INSERT INTO outbox_events VALUES (:id, :tenant, :type, CAST(:payload AS jsonb), :now)"
        ),
        parameters,
    )
    uow.session.execute(
        text(
            "INSERT INTO outbox_deliveries (organization_id, event_id, consumer) "
            "VALUES (:tenant, :id, :consumer)"
        ),
        parameters,
    )
    return identifier


def dispatch_batch(engine: Engine, publish: Publisher, *, now: datetime, limit: int = 25) -> int:
    if not 1 <= limit <= 100:
        raise ValueError("Dispatch batch must contain 1 to 100 events")
    # Commit the lease before touching Redis. A crash recovers once the lease expires.
    with engine.begin() as connection:
        rows = connection.execute(
            text("""
            WITH due AS (
                SELECT organization_id, event_id, consumer FROM outbox_deliveries
                WHERE completed_at IS NULL AND failed_at IS NULL AND next_attempt_at <= :now
                ORDER BY next_attempt_at, event_id LIMIT :limit FOR UPDATE SKIP LOCKED
            )
            UPDATE outbox_deliveries d
            SET attempts = d.attempts + 1, next_attempt_at = :now + interval '30 seconds'
            FROM due WHERE d.organization_id = due.organization_id
                AND d.event_id = due.event_id AND d.consumer = due.consumer
            RETURNING d.organization_id, d.event_id, d.consumer
        """),
            {"now": now, "limit": limit},
        ).all()
    for tenant, event, consumer in rows:
        # Payload is never transported through the broker; workers reread PostgreSQL.
        publish(str(tenant), str(event), consumer)
    return len(rows)


def consume(
    sessions: sessionmaker[Session],
    context: TenantContext,
    event_id: UUID,
    consumer: str,
    handler: Handler,
    clock: Clock,
) -> bool:
    with UnitOfWork(sessions, context) as uow:
        delivery = uow.session.execute(
            text("""
            SELECT completed_at, failed_at FROM outbox_deliveries
            WHERE organization_id = :tenant AND event_id = :event AND consumer = :consumer
            FOR UPDATE
        """),
            {"tenant": context.organization_id, "event": event_id, "consumer": consumer},
        ).first()
        if delivery is None or delivery.completed_at is not None or delivery.failed_at is not None:
            return False
        payload = uow.session.execute(
            text("""
            SELECT event_type, payload FROM outbox_events
            WHERE organization_id = :tenant AND id = :event
        """),
            {"tenant": context.organization_id, "event": event_id},
        ).one()
        handler(
            uow.session, context, {"event_type": payload.event_type, "payload": payload.payload}
        )
        values = {
            "tenant": context.organization_id,
            "event": event_id,
            "consumer": consumer,
            "now": clock.now(),
        }
        uow.session.execute(
            text("""
            INSERT INTO consumer_receipts VALUES (:tenant, :event, :consumer, :now)
        """),
            values,
        )
        uow.session.execute(
            text("""
            UPDATE outbox_deliveries SET completed_at = :now
            WHERE organization_id = :tenant AND event_id = :event AND consumer = :consumer
        """),
            values,
        )
        uow.commit()
        return True
