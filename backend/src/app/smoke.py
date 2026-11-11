"""Probe the real UI/API and dispatch an infrastructure event through the worker."""

import time
from uuid import uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.context import SystemClock, TenantContext
from app.core.database import UnitOfWork, make_engine
from app.workers.outbox import enqueue


def main() -> None:
    with httpx.Client(timeout=5, trust_env=False) as client:
        for path in ("/", "/guide", "/health/ready", "/api/v1/openapi.json"):
            response = client.get(f"http://127.0.0.1:18173{path}")
            if response.status_code != 200:
                raise RuntimeError("Application HTTP probe failed")
        if client.get("http://127.0.0.1:18173/health/ready").json() != {"status": "ok"}:
            raise RuntimeError("Readiness response is invalid")
    engine = make_engine(Settings())
    sessions = sessionmaker(engine)
    tenant = TenantContext(uuid4(), uuid4(), principal="system")
    try:
        with UnitOfWork(sessions, tenant) as uow:
            identifier = enqueue(
                uow,
                event_type="system.probe",
                payload={},
                consumer="system.probe",
                clock=SystemClock(),
            )
            uow.commit()
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            with UnitOfWork(sessions, tenant) as uow:
                count = uow.session.scalar(
                    text("SELECT count(*) FROM consumer_receipts WHERE event_id=:id"),
                    {"id": identifier},
                )
                if count == 1:
                    print("UI, same-origin API, readiness and real dispatcher/worker receipt OK")
                    return
            time.sleep(0.25)
        raise RuntimeError("Worker did not consume the probe within the bounded deadline")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
