import signal
import threading
from pathlib import Path

from app.core.config import Settings
from app.core.context import SystemClock
from app.core.database import make_engine
from app.workers.outbox import dispatch_batch


def main() -> None:
    from app.workers.celery_app import celery

    engine = make_engine(Settings(process="dispatcher"), dispatcher=True)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    def publish(tenant: str, event: str, consumer: str) -> None:
        celery.send_task("pms.consume", args=[tenant, event, consumer])

    try:
        while not stop.is_set():
            try:
                dispatch_batch(engine, publish, now=SystemClock().now())
                Path("/tmp/dispatcher-heartbeat").touch()  # noqa: S108 - private container tmpfs
            except Exception:
                print('{"service":"dispatcher","code":"dispatch_unavailable"}', flush=True)
            stop.wait(2)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
