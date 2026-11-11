"""Lose a real broker message, then recover from PostgreSQL, on owned resources."""

import os
import re
import secrets
import shutil
import subprocess
import time
from datetime import timedelta
from uuid import uuid4

import pytest
from celery import Celery
from redis import Redis
from sqlalchemy import Engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.context import SystemClock, TenantContext
from app.core.database import UnitOfWork, make_engine
from app.workers.outbox import dispatch_batch, enqueue

pytestmark = pytest.mark.integration


def test_real_redis_loss_recovers_from_postgres(
    database: Settings,
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if os.environ.get("PMS_BROKER_RECOVERY") != "1":
        pytest.skip("Run application.py test --broker-recovery after building Compose images")
    executable = shutil.which("docker")
    assert executable is not None
    project = os.environ["PMS_COMPOSE_PROJECT"]
    assert re.fullmatch(r"[a-z0-9][a-z0-9_-]*", project)
    suffix = uuid4().hex
    broker_name, worker_name, queue = (
        f"pms_recovery_{kind}_{suffix}" for kind in ("redis", "worker", "queue")
    )
    password = secrets.token_hex(24)
    monkeypatch.setenv("PMS_RECOVERY_PASSWORD", password)

    def docker(*arguments: str, environment: dict[str, str] | None = None) -> str:
        result = subprocess.run(  # noqa: S603 - fixed executable and argument list
            [executable, *arguments],
            capture_output=True,
            text=True,
            timeout=60,
            env=environment or os.environ,
            check=False,
        )
        if result.returncode:
            raise RuntimeError("Isolated broker test Docker operation failed; output withheld")
        return result.stdout.strip()

    image = docker("inspect", f"{project}-redis-1", "--format", "{{.Config.Image}}")
    environment = {
        **os.environ,
        "REDIS_PASSWORD": password,
        "PMS_ENVIRONMENT": "test",
        "PMS_PROCESS": "worker",
        "PMS_DATABASE_HOST": "postgres",
        "PMS_DATABASE_PORT": "5432",
        "PMS_DATABASE_NAME": database.database_name,
        "PMS_REDIS_HOST": broker_name,
        "PMS_REDIS_PORT": "6379",
        "PMS_REDIS_PASSWORD": password,
        "PMS_QUEUE_NAME": queue,
    }
    dispatcher = make_engine(database, dispatcher=True)
    client = None
    try:
        docker(
            "run",
            "-d",
            "--name",
            broker_name,
            "--network",
            f"{project}_business",
            "-p",
            "127.0.0.1::6379",
            "--env",
            "REDIS_PASSWORD",
            image,
            "sh",
            "-c",
            'exec redis-server --save "" --appendonly no --requirepass "$REDIS_PASSWORD"',
            environment=environment,
        )
        port = int(
            docker(
                "inspect",
                broker_name,
                "--format",
                '{{(index (index .NetworkSettings.Ports "6379/tcp") 0).HostPort}}',
            )
        )
        client = Redis(host="127.0.0.1", port=port, password=password, socket_timeout=2)

        def wait_for_broker() -> None:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    if client.ping():
                        return
                except Exception:  # noqa: S110 - bounded probe, no credential-bearing exception log
                    pass
                time.sleep(0.1)
            raise RuntimeError("Isolated broker did not become ready")

        wait_for_broker()
        sessions, clock = sessionmaker(engine), SystemClock()
        context = TenantContext(uuid4(), uuid4(), principal="system")
        with UnitOfWork(sessions, context) as uow:
            identifier = enqueue(
                uow, event_type="system.probe", payload={}, consumer="system.probe", clock=clock
            )
            uow.commit()
        broker = Celery("recovery", broker=f"redis://:{password}@127.0.0.1:{port}/0")
        broker.conf.update(task_default_queue=queue, task_publish_retry=False)

        def publish(tenant: str, event: str, consumer: str) -> None:
            broker.send_task("pms.consume", args=[tenant, event, consumer])

        now = clock.now() + timedelta(seconds=1)
        dispatch_batch(dispatcher, publish, now=now)
        assert client.llen(queue) >= 1
        # No worker has started: restart this volatile, owned broker to lose its message.
        docker("restart", broker_name)
        # Docker Desktop can assign another ephemeral host port on restart.
        # The worker uses the stable container DNS name; refresh only the host probe.
        port = int(
            docker(
                "inspect",
                broker_name,
                "--format",
                '{{(index (index .NetworkSettings.Ports "6379/tcp") 0).HostPort}}',
            )
        )
        client.close()
        broker.close()
        client = Redis(host="127.0.0.1", port=port, password=password, socket_timeout=2)
        broker = Celery("recovery", broker=f"redis://:{password}@127.0.0.1:{port}/0")
        broker.conf.update(task_default_queue=queue, task_publish_retry=False)
        wait_for_broker()
        assert client.llen(queue) == 0
        docker(
            "run",
            "-d",
            "--name",
            worker_name,
            "--network",
            f"{project}_business",
            *[
                argument
                for key in (
                    "PMS_ENVIRONMENT",
                    "PMS_PROCESS",
                    "PMS_DATABASE_HOST",
                    "PMS_DATABASE_PORT",
                    "PMS_DATABASE_NAME",
                    "PMS_DATABASE_PASSWORD",
                    "PMS_REDIS_HOST",
                    "PMS_REDIS_PORT",
                    "PMS_REDIS_PASSWORD",
                    "PMS_QUEUE_NAME",
                )
                for argument in ("--env", key)
            ],
            f"{project}-worker",
            "celery",
            "-A",
            "app.workers.celery_app:celery",
            "worker",
            "--concurrency=1",
            "--loglevel=WARNING",
            "--without-gossip",
            "--without-mingle",
            environment=environment,
        )
        # Advance the injected dispatch clock past the committed lease, not wall-clock sleep.
        dispatch_batch(dispatcher, publish, now=now + timedelta(seconds=31))
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            with UnitOfWork(sessions, context) as uow:
                receipts = uow.session.scalar(
                    text("SELECT count(*) FROM consumer_receipts WHERE event_id=:id"),
                    {"id": identifier},
                )
            if receipts == 1:
                break
            time.sleep(0.1)
        else:
            pytest.fail("Durable event was not consumed after real Redis message loss")
        # Deliver the same envelope again and verify no second durable receipt appears.
        publish(str(context.organization_id), str(identifier), "system.probe")
        with UnitOfWork(sessions, context) as uow:
            assert (
                uow.session.scalar(
                    text("SELECT count(*) FROM consumer_receipts WHERE event_id=:id"),
                    {"id": identifier},
                )
                == 1
            )
        broker.close()
    finally:
        if client is not None:
            client.close()
        dispatcher.dispose()
        # Exact names created by this test, no volumes, no existing stack affected.
        for name in (worker_name, broker_name):
            assert name.endswith(suffix) and name.startswith("pms_recovery_")
            subprocess.run(  # noqa: S603 - exact owned container names
                [executable, "rm", "-f", name], capture_output=True, timeout=30, check=False
            )
