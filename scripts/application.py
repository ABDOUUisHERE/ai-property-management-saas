"""Local application commands; credentials stay in process environment, never argv."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import jwt
import psycopg
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.dev import ROOT, init_environment, read_env, validate_env  # noqa: E402


def application_environment(env_file: Path) -> dict[str, str]:
    """The validated local file owns the PMS namespace, including its target DB."""
    values = read_env(env_file)
    validate_env(values)
    return {
        **{key: value for key, value in os.environ.items() if not key.startswith("PMS_")},
        "PMS_ENVIRONMENT": "local",
        "PMS_PROCESS": "api",
        "PMS_DATABASE_HOST": "127.0.0.1",
        "PMS_DATABASE_PORT": values["DATABASE_PORT"],
        "PMS_DATABASE_NAME": "property_management",
        "PMS_DATABASE_PASSWORD": values["DATABASE_RUNTIME_PASSWORD"],
        "PMS_MIGRATION_PASSWORD": values["DATABASE_MIGRATION_PASSWORD"],
        "PMS_DISPATCH_PASSWORD": values["DATABASE_DISPATCH_PASSWORD"],
        "PMS_REDIS_HOST": "127.0.0.1",
        "PMS_REDIS_PORT": values["REDIS_PORT"],
        "PMS_REDIS_PASSWORD": values["REDIS_PASSWORD"],
    }


def provision_dispatcher(env_file: Path) -> None:
    values = read_env(env_file)
    validate_env(values)
    with psycopg.connect(
        host="127.0.0.1",
        port=int(values["DATABASE_PORT"]),
        user="pms_admin",
        dbname="property_management",
        password=values["DATABASE_ADMIN_PASSWORD"],
        connect_timeout=3,
    ) as connection:
        if not connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname='pms_dispatcher'"
        ).fetchone():
            connection.execute(
                sql.SQL(
                    "CREATE ROLE pms_dispatcher LOGIN PASSWORD {} "
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS"
                ).format(sql.Literal(values["DATABASE_DISPATCH_PASSWORD"]))
            )
            connection.execute("GRANT CONNECT ON DATABASE property_management TO pms_dispatcher")
    print("Dedicated dispatcher role provisioned; existing roles preserved")


def run_backend(
    arguments: list[str], env_file: Path, *, testing: bool = False, broker_recovery: bool = False
) -> None:
    executable = shutil.which("uv")
    if not executable:
        raise RuntimeError("uv is required")
    environment = application_environment(env_file)
    environment.pop("VIRTUAL_ENV", None)
    if arguments[0] == "uvicorn":
        environment.pop("PMS_MIGRATION_PASSWORD", None)
        environment.pop("PMS_DISPATCH_PASSWORD", None)
    if testing:
        values = read_env(env_file)
        environment["PMS_TEST_ADMIN_PASSWORD"] = values["DATABASE_ADMIN_PASSWORD"]
        environment["PMS_INTEGRATION"] = "1"
        environment["PMS_COMPOSE_PROJECT"] = read_env(env_file)["COMPOSE_PROJECT_NAME"]
        environment["PMS_BROKER_RECOVERY"] = "1" if broker_recovery else "0"
        # A short-lived fixture capability exists only in the test child. The API,
        # worker and dispatcher never receive Auth administration keys or tokens.
        key = json.loads(values["AUTH_JWT_KEYS"])[0]
        now = int(time.time())
        environment["PMS_TEST_AUTH_URL"] = values["AUTH_EXTERNAL_URL"]
        environment["PMS_TEST_MAIL_URL"] = f"http://127.0.0.1:{values['MAILPIT_HTTP_PORT']}"
        environment["PMS_TEST_AUTH_ADMIN_TOKEN"] = jwt.encode(
            {
                "role": "service_role",
                "aud": "authenticated",
                "iss": values["AUTH_EXTERNAL_URL"],
                "iat": now,
                "exp": now + 300,
            },
            jwt.PyJWK.from_dict(key).key,
            algorithm="ES256",
            headers={"kid": key["kid"]},
        )
    result = subprocess.run(  # noqa: S603 - fixed executable, list arguments, no shell
        [executable, "run", "--locked", *arguments],
        cwd=ROOT / "backend",
        env=environment,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Backend command failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "migrate", "api", "test", "export", "smoke"))
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--broker-recovery", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        init_environment(env_file=args.env_file)
        provision_dispatcher(args.env_file)
    elif args.command == "migrate":
        run_backend(["alembic", "upgrade", "head"], args.env_file)
    elif args.command == "api":
        run_backend(
            [
                "uvicorn",
                "app.main:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                "18000",
                "--no-access-log",
                "--no-proxy-headers",
            ],
            args.env_file,
        )
    elif args.command == "test":
        run_backend(["pytest"], args.env_file, testing=True, broker_recovery=args.broker_recovery)
    elif args.command == "export":
        run_backend(["python", "-m", "app.export_openapi"], args.env_file)
    elif args.command == "smoke":
        run_backend(["python", "-m", "app.smoke"], args.env_file)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Application command failed: {type(error).__name__}", file=sys.stderr)
        sys.exit(1)
