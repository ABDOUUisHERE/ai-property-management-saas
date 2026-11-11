from pathlib import Path
from typing import Any
from uuid import UUID

from celery import Celery
from celery.signals import heartbeat_sent
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.context import SystemClock, TenantContext
from app.core.database import UnitOfWork, make_engine
from app.workers.outbox import consume

settings = Settings()
celery = Celery("property_management", broker=settings.broker_url())
celery.conf.update(
    task_default_queue=settings.queue_name,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    broker_transport_options={"visibility_timeout": 60, "socket_timeout": 3},
    broker_connection_timeout=3,
    task_publish_retry=False,
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,
    task_soft_time_limit=10,
    task_time_limit=15,
    worker_hijack_root_logger=False,
    worker_redirect_stdouts=False,
)


@heartbeat_sent.connect  # type: ignore[untyped-decorator]
def heartbeat(**kwargs: Any) -> None:
    Path("/tmp/worker-heartbeat").touch()  # noqa: S108 - private container tmpfs


def probe(session: Session, context: TenantContext, envelope: dict[str, Any]) -> None:
    """Infrastructure receipt only; no pretend business action."""
    if envelope["event_type"] != "system.probe":
        raise ValueError("Unsupported event type")


@celery.task(name="pms.consume")  # type: ignore[untyped-decorator]
def consume_event(tenant: str, event: str, consumer: str) -> None:
    context = TenantContext(UUID(tenant), UUID(int=0), principal="system")
    identifier = UUID(event)
    engine = make_engine(settings)
    sessions = sessionmaker(engine, expire_on_commit=False)
    try:
        try:
            if consumer != "system.probe":
                raise ValueError("Unknown consumer")
            consume(sessions, context, identifier, consumer, probe, SystemClock())
        except Exception:
            # Persist a bounded failure state without exception text or payloads.
            # Successful broker delivery is not success: the dispatcher will redeliver.
            with UnitOfWork(sessions, context) as uow:
                uow.session.execute(
                    text("""
                    UPDATE outbox_deliveries SET error_code = 'consumer_failed',
                        failed_at = CASE WHEN attempts >= 8 THEN now() ELSE NULL END
                    WHERE organization_id = :tenant AND event_id = :event
                        AND consumer = :consumer AND completed_at IS NULL
                """),
                    {"tenant": context.organization_id, "event": identifier, "consumer": consumer},
                )
                uow.commit()
    finally:
        engine.dispose()
