"""Guard against leaking credentials, overwriting volumes' keys or testing a remote service."""

import copy
import json
import shutil
import time
from types import SimpleNamespace
from pathlib import Path

import jwt
import pytest

from scripts.application import application_environment, run_backend
from scripts.dev import (
    ROOT,
    SECRET_KEYS,
    init_environment,
    read_env,
    signing_key,
    validate_env,
    verify_token,
)


@pytest.fixture
def initialized(tmp_path: Path) -> Path:
    shutil.copyfile(ROOT / ".env.example", tmp_path / ".env.example")
    assert init_environment(tmp_path)
    return tmp_path


def test_second_init_preserves_all_provisioned_credentials(initialized: Path) -> None:
    path = initialized / ".env"
    before = path.read_bytes()
    assert not init_environment(initialized)
    assert path.read_bytes() == before


def test_application_target_and_credentials_ignore_inherited_shell_values(
    initialized: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PMS_DATABASE_NAME", "another_existing_database")
    monkeypatch.setenv("PMS_PROCESS", "dispatcher")
    monkeypatch.setenv("PMS_TEST_ADMIN_PASSWORD", "x" * 48)
    monkeypatch.setenv("PMS_DATABASE_HOST", "unrelated.example.test")
    environment = application_environment(initialized / ".env")
    assert environment["PMS_DATABASE_NAME"] == "property_management"
    assert environment["PMS_DATABASE_HOST"] == "127.0.0.1"
    assert environment["PMS_PROCESS"] == "api"
    assert "PMS_TEST_ADMIN_PASSWORD" not in environment


def test_migration_child_does_not_receive_browser_session_secrets(initialized, monkeypatch):
    observed = []
    monkeypatch.setattr("scripts.application.shutil.which", lambda name: "uv")

    def child(*args, **kwargs):
        observed.append(set(kwargs["env"]))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("scripts.application.subprocess.run", child)
    run_backend(["alembic", "upgrade", "head"], initialized / ".env")
    assert "PMS_MIGRATION_PASSWORD" in observed[0]
    assert "PMS_SESSION_KEYS" not in observed[0] and "PMS_CSRF_SECRET" not in observed[0]


def test_generated_service_credentials_are_distinct_and_not_template_values(
    initialized: Path,
) -> None:
    values = read_env(initialized / ".env")
    validate_env(values)
    assert len({values[key] for key in SECRET_KEYS}) == len(SECRET_KEYS)
    assert "__GENERATE__" not in values.values()


def test_p01_environment_upgrade_adds_only_dispatcher_credential(initialized: Path) -> None:
    path = initialized / ".env"
    original = read_env(path)
    original.pop("DATABASE_DISPATCH_PASSWORD")
    path.write_text(
        "\n".join(f"{key}='{value}'" for key, value in original.items()), encoding="utf-8"
    )
    before = path.read_bytes()
    assert not init_environment(initialized)
    after = read_env(path)
    assert {key: after[key] for key in original} == original
    assert path.read_bytes().startswith(before)
    assert len(after["DATABASE_DISPATCH_PASSWORD"]) == 48
    upgraded = path.read_bytes()
    assert not init_environment(initialized)
    assert path.read_bytes() == upgraded


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("APP_ENV", "production"),
        ("AUTH_EXTERNAL_URL", "https://auth.example.com"),
        ("APP_SITE_URL", "http://user:password@127.0.0.1:5173"),
        ("APP_SITE_URL", "http://example.com"),
        ("REDIS_PORT", "15432"),
        ("DATABASE_ADMIN_PASSWORD", "__GENERATE__"),
    ],
)
def test_config_rejects_remote_targets_and_incomplete_or_conflicting_values(
    initialized: Path,
    key: str,
    value: str,
) -> None:
    values = read_env(initialized / ".env")
    values[key] = value
    with pytest.raises(ValueError):
        validate_env(values)


def test_invalid_existing_env_is_not_replaced(initialized: Path) -> None:
    path = initialized / ".env"
    path.write_text("APP_ENV=production\n", encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(ValueError):
        init_environment(initialized)
    assert path.read_bytes() == before


def test_p02_upgrade_preserves_credentials_and_adds_separate_session_secrets(initialized: Path):
    path = initialized / ".env"
    original = read_env(path)
    original.pop("SESSION_ENCRYPTION_KEY")
    original.pop("CSRF_SECRET")
    path.write_text(
        "\n".join(f"{key}='{value}'" for key, value in original.items()), encoding="utf-8"
    )
    before = path.read_bytes()
    assert not init_environment(initialized)
    upgraded = read_env(path)
    assert {key: upgraded[key] for key in original} == original
    assert path.read_bytes().startswith(before)
    assert len(upgraded["CSRF_SECRET"]) == 64
    second = path.read_bytes()
    assert not init_environment(initialized)
    assert path.read_bytes() == second


def test_duplicate_env_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("APP_ENV=local\nAPP_ENV=production\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        read_env(path)


def test_es256_private_key_and_public_jwks_are_interoperable() -> None:
    private = signing_key()
    public = copy.deepcopy(private)
    public.pop("d")
    public["key_ops"] = ["verify"]
    token = jwt.encode({"sub": "fixture"}, jwt.PyJWK.from_dict(private).key, algorithm="ES256")
    assert (
        jwt.decode(token, jwt.PyJWK.from_dict(public).key, algorithms=["ES256"])["sub"] == "fixture"
    )
    assert "d" not in json.loads(json.dumps(public))
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, jwt.PyJWK.from_dict(signing_key()).key, algorithms=["ES256"])


@pytest.mark.parametrize(
    ("issuer", "audience", "offset", "error"),
    [
        ("http://127.0.0.1:19999", "authenticated", 2, None),
        ("http://127.0.0.1:19999", "authenticated", 60, jwt.ImmatureSignatureError),
        ("http://wrong-issuer.test", "authenticated", 0, jwt.InvalidIssuerError),
        ("http://127.0.0.1:19999", "wrong-audience", 0, jwt.InvalidAudienceError),
    ],
)
def test_auth_validation_bounds_clock_skew_and_still_checks_issuer_and_audience(
    issuer: str,
    audience: str,
    offset: int,
    error: type[Exception] | None,
) -> None:
    private = signing_key()
    public = {key: value for key, value in private.items() if key != "d"}
    public["key_ops"] = ["verify"]
    now = int(time.time())
    token = jwt.encode(
        {"sub": "fixture", "iss": issuer, "aud": audience, "iat": now + offset, "exp": now + 300},
        jwt.PyJWK.from_dict(private).key,
        algorithm="ES256",
        headers={"kid": private["kid"]},
    )
    if error:
        with pytest.raises(error):
            verify_token(token, {"keys": [public]}, "http://127.0.0.1:19999")
    else:
        assert verify_token(token, {"keys": [public]}, issuer)["sub"] == "fixture"
