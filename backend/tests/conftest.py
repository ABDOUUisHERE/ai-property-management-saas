import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import Engine

from app.core.config import Settings
from app.core.database import make_engine


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    secrets = [
        value
        for key, value in os.environ.items()
        if key.startswith("PMS_")
        and any(marker in key for marker in ("PASSWORD", "TOKEN", "SECRET", "KEY"))
        and len(value) >= 24
    ]
    if report.failed:
        rendered = str(report.longrepr)
        for secret in secrets:
            rendered = rendered.replace(secret, "<REDACTED>")
        report.longrepr = rendered
    report.sections = [(name, redact(content, secrets)) for name, content in report.sections]


def redact(content: str, secrets: list[str]) -> str:
    for secret in secrets:
        content = content.replace(secret, "<REDACTED>")
    return content


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="test",
        database_password="a" * 48,
        redis_password="b" * 48,
        database_port=1,
        database_timeout_seconds=1,
    )


@pytest.fixture(scope="session")
def database() -> Iterator[Settings]:
    if os.environ.get("PMS_INTEGRATION") != "1":
        pytest.skip("Use scripts/application.py test for real PostgreSQL integration")
    base = Settings()
    if base.database_host != "127.0.0.1" or base.environment not in {"local", "test"}:
        pytest.fail("Integration tests require an explicit local target")
    name = f"pms_test_{uuid4().hex}"
    admin = dict(
        host=base.database_host,
        port=base.database_port,
        user="pms_admin",
        password=os.environ["PMS_TEST_ADMIN_PASSWORD"],
        connect_timeout=3,
    )
    with psycopg.connect(dbname="property_management", autocommit=True, **admin) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {} OWNER pms_migrator").format(sql.Identifier(name))
        )
    configuration = base.model_copy(
        update={"environment": "test", "database_name": name, "pool_size": 1}
    )
    old_name = os.environ.get("PMS_DATABASE_NAME")
    os.environ["PMS_DATABASE_NAME"] = name
    try:
        migration = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.upgrade(migration, "head")
        command.upgrade(migration, "head")
        command.downgrade(migration, "base")
        command.upgrade(migration, "head")
        yield configuration
    finally:
        if old_name is None:
            os.environ.pop("PMS_DATABASE_NAME", None)
        else:
            os.environ["PMS_DATABASE_NAME"] = old_name
        # Exact database created by this fixture; never the developer database.
        assert name.startswith("pms_test_") and len(name) == 41
        with psycopg.connect(dbname="property_management", autocommit=True, **admin) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


@pytest.fixture
def engine(database: Settings) -> Iterator[Engine]:
    resource = make_engine(database)
    try:
        yield resource
    finally:
        resource.dispose()
