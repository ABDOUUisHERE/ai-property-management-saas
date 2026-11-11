import base64
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from threading import Event
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.database import make_engine
from app.modules.identity.contracts import (
    AuthenticatedAccount,
    AuthenticationRejected,
    ProviderTokens,
    ProviderUnavailable,
    RefreshUncertain,
    VerifiedIdentity,
)
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.sessions import SessionBusy, SessionExpired, SessionService, session_hash
from app.modules.identity.vault import TokenVault

pytestmark = pytest.mark.integration


@dataclass
class Clock:
    instant: datetime

    def now(self):
        return self.instant

    def advance(self, **kwargs):
        self.instant += timedelta(**kwargs)


class Authority:
    """Realistic test authority; the production adapter has its own JWT/HTTP tests."""

    def __init__(self, clock):
        self.clock, self.subject = clock, uuid4()
        self.accounts = {}
        self.refreshes, self.logouts = 0, 0
        self.entered, self.release = Event(), Event()
        self.block_refresh = False
        self.refresh_failure = None
        self.verification_failure = None
        self.logout_failure = False
        self.before_refresh = lambda: None
        self.before_verify = lambda: None
        self.before_logout = lambda: None

    def _account(self, session):
        now = self.clock.now().replace(microsecond=0)
        identity = VerifiedIdentity(self.subject, session, now, now + timedelta(minutes=15))
        account = AuthenticatedAccount(
            identity,
            "fiction@example.test",
            ProviderTokens(
                SecretStr(secrets.token_urlsafe(40)),
                SecretStr(secrets.token_urlsafe(40)),
            ),
        )
        self.accounts[account.tokens.access_token.get_secret_value()] = account
        self.accounts[account.tokens.refresh_token.get_secret_value()] = account
        return account

    def login(self, email, password):
        return self._account(uuid4())

    def verify_access(self, access_token):
        self.before_verify()
        if self.verification_failure:
            raise self.verification_failure()
        account = self.accounts[access_token.get_secret_value()]
        if account.identity.expires_at <= self.clock.now():
            raise AuthenticationRejected()
        return account.identity

    def refresh(self, refresh_token, *, expected_subject, expected_session_id):
        self.before_refresh()
        self.refreshes += 1
        self.entered.set()
        if self.block_refresh:
            assert self.release.wait(10), "Refresh test was not released"
        if self.refresh_failure:
            raise self.refresh_failure()
        old = self.accounts[refresh_token.get_secret_value()]
        assert old.identity.subject == expected_subject
        assert old.identity.provider_session_id == expected_session_id
        return self._account(expected_session_id)

    def logout(self, access_token):
        self.before_logout()
        self.logouts += 1
        if self.logout_failure:
            raise ProviderUnavailable()


@pytest.fixture
def identity(engine):
    clock = Clock(datetime.now(UTC))
    repository = IdentityRepository(sessionmaker(engine))
    authority = Authority(clock)
    key = SecretStr(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    vault = TokenVault({"initial": key}, active_key_id="initial")
    service = SessionService(repository, authority, vault, clock)
    return service, repository, authority, clock, key


def login(service):
    return service.login("fiction@example.test", SecretStr("fictional-password"))


def stored(repository, session):
    capability = session_hash(session.opaque)
    with repository.transaction(session_hash=capability) as transaction:
        return transaction.lock_session(capability)


def test_profile_is_unique_under_repeated_and_concurrent_login(identity, engine):
    service, repository, authority, clock, _ = identity
    with ThreadPoolExecutor(max_workers=2) as pool:
        sessions = list(pool.map(lambda _: login(service), range(2)))
    assert sessions[0].profile.id == sessions[1].profile.id
    assert sessions[0].opaque != sessions[1].opaque
    for session in sessions:
        assert service.resolve(session.opaque) == session.profile
        assert len(session.opaque.get_secret_value()) == 43
        record = stored(repository, session)
        assert session.opaque.get_secret_value() not in record.encrypted_tokens
        assert record.absolute_expires_at == clock.now() + timedelta(hours=24)
    with repository.transaction(
        session_hash=session_hash(sessions[0].opaque), verified_subject=authority.subject
    ) as transaction:
        profile = transaction.upsert_profile(authority.subject, "updated@example.test", clock.now())
        assert profile.id == sessions[0].profile.id
    assert service.resolve(sessions[0].opaque).email == "updated@example.test"
    assert engine.pool.checkedout() == 0


def test_runtime_identity_policies_deny_absent_and_foreign_context(identity, engine):
    service, repository, authority, clock, _ = identity
    session = login(service)
    capability = session_hash(session.opaque)
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT count(*) FROM users")) == 0
        assert connection.scalar(text("SELECT count(*) FROM auth_sessions")) == 0
        assert connection.execute(
            text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user")
        ).one() == (False, False)
        assert connection.execute(
            text(
                "SELECT bool_and(relrowsecurity AND relforcerowsecurity) FROM pg_class "
                "WHERE relname IN ('users','auth_sessions')"
            )
        ).scalar_one()
    other_hash, other_subject = secrets.token_hex(32), uuid4()
    with repository.transaction(session_hash=other_hash, verified_subject=other_subject) as tx:
        assert tx.lock_session(capability) is None
        assert tx.profile(session.profile.id) is None
    with (
        pytest.raises(DBAPIError),
        repository.transaction(session_hash=other_hash, verified_subject=other_subject) as tx,
    ):
        tx.upsert_profile(authority.subject, "foreign@example.test", clock.now())
    with repository.transaction(session_hash=capability) as tx:
        assert tx.profile(session.profile.id) == session.profile
    with engine.connect() as connection:
        for setting in ("app.auth_subject", "app.session_hash", "app.organization_id"):
            assert (
                connection.scalar(
                    text("SELECT nullif(current_setting(:key,true), '')"), {"key": setting}
                )
                is None
            )


def test_dispatcher_has_no_identity_access_and_migration_owner_obeys_force_rls(identity, database):
    service, _, authority, _, _ = identity
    login(service)
    dispatcher = make_engine(database, dispatcher=True)
    try:
        with pytest.raises(DBAPIError), dispatcher.connect() as connection:
            connection.execute(text("SELECT * FROM users"))
        with pytest.raises(DBAPIError), dispatcher.connect() as connection:
            connection.execute(text("SELECT * FROM auth_sessions"))
    finally:
        dispatcher.dispose()
    migrator = create_engine(
        URL.create(
            "postgresql+psycopg",
            username="pms_migrator",
            password=os.environ["PMS_MIGRATION_PASSWORD"],
            host=database.database_host,
            port=database.database_port,
            database=database.database_name,
        ),
        poolclass=NullPool,
        hide_parameters=True,
    )
    try:
        with migrator.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.auth_subject', :subject, true)"),
                {"subject": str(authority.subject)},
            )
            assert connection.scalar(text("SELECT count(*) FROM users")) == 0
            assert connection.scalar(text("SELECT count(*) FROM auth_sessions")) == 0
    finally:
        migrator.dispose()


def test_session_capability_cannot_edit_profile_email_without_verified_subject(identity, engine):
    service, _, _, _, _ = identity
    session = login(service)
    with engine.begin() as connection:
        connection.execute(
            text("SELECT set_config('app.session_hash', :hash, true)"),
            {"hash": session_hash(session.opaque)},
        )
        rows = connection.execute(
            text("UPDATE users SET email='injected@example.test' RETURNING id")
        )
        assert rows.all() == []
    assert service.resolve(session.opaque) == session.profile


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE users SET auth_subject='00000000-0000-0000-0000-000000000001'::uuid",
        "UPDATE users SET id='00000000-0000-0000-0000-000000000001'::uuid",
        "UPDATE auth_sessions SET user_id='00000000-0000-0000-0000-000000000001'::uuid",
        "UPDATE auth_sessions SET auth_subject='00000000-0000-0000-0000-000000000001'::uuid",
        "UPDATE auth_sessions SET session_hash=repeat('a',64)",
        "UPDATE auth_sessions SET absolute_expires_at=now()+interval '7 days'",
    ],
)
def test_runtime_cannot_rebind_subject_or_extend_absolute_session(identity, engine, statement):
    service, _, authority, _, _ = identity
    session = login(service)
    with (
        pytest.raises(DBAPIError),
        engine.begin() as connection,
    ):
        connection.execute(
            text(
                "SELECT set_config('app.session_hash', :hash, true), "
                "set_config('app.auth_subject', :subject, true)"
            ),
            {"hash": session_hash(session.opaque), "subject": str(authority.subject)},
        )
        connection.execute(text(statement))


def test_identity_foreign_key_and_rollback_protect_profile_link(identity):
    service, repository, authority, clock, _ = identity
    original = login(service)
    record = stored(repository, original)
    foreign, capability = uuid4(), secrets.token_hex(32)
    with (
        pytest.raises(DBAPIError),
        repository.transaction(session_hash=capability, verified_subject=foreign) as tx,
    ):
        foreign_profile = tx.upsert_profile(foreign, "other@example.test", clock.now())
        tx.insert_session(replace(record, session_hash=capability, auth_subject=foreign))
    with repository.transaction(session_hash=capability, verified_subject=foreign) as tx:
        assert tx.profile(foreign_profile.id) is None
        assert tx.profile(original.profile.id) is None
        assert tx.lock_session(capability) is None
    assert service.resolve(original.opaque) == original.profile


def test_login_failure_rolls_back_and_provider_session_is_closed(identity, monkeypatch):
    service, repository, authority, _, _ = identity
    from app.modules.identity.repository import IdentityTransaction

    original_insert = IdentityTransaction.insert_session
    attempted = []

    def fail_after_profile(self, record):
        attempted.append(record)
        raise SQLAlchemyError("simulated persistence failure")

    monkeypatch.setattr(IdentityTransaction, "insert_session", fail_after_profile)
    with pytest.raises(SQLAlchemyError):
        login(service)
    assert authority.logouts == 1
    with repository.transaction(
        session_hash=attempted[0].session_hash, verified_subject=authority.subject
    ) as tx:
        assert tx.profile(attempted[0].user_id) is None
    monkeypatch.setattr(IdentityTransaction, "insert_session", original_insert)
    recovered = login(service)
    assert service.resolve(recovered.opaque) == recovered.profile


def test_refresh_does_not_extend_absolute_lifetime(identity, engine):
    service, repository, authority, clock, _ = identity
    session = login(service)
    authority.before_refresh = lambda: assert_no_connection(engine)
    clock.advance(minutes=15)
    assert service.resolve(session.opaque) == session.profile
    record = stored(repository, session)
    assert authority.refreshes == 1
    assert record.version == 2 and record.refresh_owner is None
    assert record.absolute_expires_at == session.expires_at
    clock.advance(hours=24)
    with pytest.raises(SessionExpired):
        service.resolve(session.opaque)
    assert stored(repository, session).encrypted_tokens is None
    assert authority.refreshes == 1


def assert_no_connection(engine):
    assert engine.pool.checkedout() == 0


def test_concurrent_refresh_has_one_owner_and_releases_sql_connection(identity, engine):
    service, _, authority, clock, _ = identity
    session = login(service)
    clock.advance(minutes=15)
    authority.block_refresh = True
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(service.resolve, session.opaque)
        try:
            assert authority.entered.wait(5)
            assert_no_connection(engine)
            with pytest.raises(SessionBusy):
                service.resolve(session.opaque)
            assert authority.refreshes == 1
        finally:
            authority.release.set()
        assert first.result(timeout=5) == session.profile
    assert service.resolve(session.opaque) == session.profile
    assert authority.refreshes == 1


@pytest.mark.parametrize("failure", [RefreshUncertain, ProviderUnavailable, AuthenticationRejected])
def test_refresh_failure_revokes_instead_of_reusing_ambiguous_tokens(identity, failure):
    service, repository, authority, clock, _ = identity
    session = login(service)
    clock.advance(minutes=15)
    authority.refresh_failure = failure
    with pytest.raises(SessionExpired):
        service.resolve(session.opaque)
    record = stored(repository, session)
    assert record.revoked_at is not None and record.encrypted_tokens is None
    with pytest.raises(SessionExpired):
        service.resolve(session.opaque)
    assert authority.refreshes == 1


@pytest.mark.parametrize("action", ["logout", "lease-expiry"])
def test_late_refresh_cannot_resurrect_revoked_session(identity, action):
    service, repository, authority, clock, _ = identity
    session = login(service)
    clock.advance(minutes=15)
    authority.block_refresh = True
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(service.resolve, session.opaque)
        try:
            assert authority.entered.wait(5)
            if action == "logout":
                service.logout(session.opaque)
            else:
                clock.advance(seconds=31)
                with pytest.raises(SessionExpired):
                    service.resolve(session.opaque)
            assert stored(repository, session).revoked_at is not None
        finally:
            authority.release.set()
        with pytest.raises(SessionExpired):
            first.result(timeout=5)
    assert stored(repository, session).encrypted_tokens is None
    with pytest.raises(SessionExpired):
        service.resolve(session.opaque)
    assert authority.refreshes == 1


def test_logout_commits_before_upstream_call_even_when_provider_is_down(identity, engine):
    service, repository, authority, _, _ = identity
    session = login(service)

    def check_committed():
        assert_no_connection(engine)
        assert stored(repository, session).revoked_at is not None

    authority.before_logout = check_committed
    authority.logout_failure = True
    service.logout(session.opaque)
    service.logout(session.opaque)
    service.logout(SecretStr("malformed"))
    assert authority.logouts == 1
    with pytest.raises(SessionExpired):
        service.resolve(session.opaque)


def test_jwks_outage_blocks_access_without_destroying_valid_session(identity, engine):
    service, repository, authority, _, _ = identity
    session = login(service)
    authority.before_verify = lambda: assert_no_connection(engine)
    authority.verification_failure = ProviderUnavailable
    with pytest.raises(ProviderUnavailable):
        service.resolve(session.opaque)
    assert stored(repository, session).revoked_at is None
    authority.verification_failure = None
    assert service.resolve(session.opaque) == session.profile
    authority.verification_failure = AuthenticationRejected
    with pytest.raises(SessionExpired):
        service.resolve(session.opaque)
    assert stored(repository, session).revoked_at is not None


def test_revocation_is_rechecked_after_jwt_verification(identity):
    service, repository, authority, _, _ = identity
    session = login(service)
    authority.before_verify = lambda: service.logout(session.opaque)
    with pytest.raises(SessionExpired):
        service.resolve(session.opaque)
    assert stored(repository, session).revoked_at is not None


def test_encryption_key_rotation_rewrites_tokens_during_refresh(identity):
    service, repository, authority, clock, old_key = identity
    session = login(service)
    new_key = SecretStr(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    rotated = SessionService(
        repository,
        authority,
        TokenVault({"initial": old_key, "rotated": new_key}, active_key_id="rotated"),
        clock,
    )
    assert rotated.resolve(session.opaque) == session.profile
    assert rotated.resolve(session.opaque, force_refresh=True) == session.profile
    assert stored(repository, session).encrypted_tokens.startswith("v1.rotated.")
    retired = SessionService(
        repository, authority, TokenVault({"rotated": new_key}, active_key_id="rotated"), clock
    )
    assert retired.resolve(session.opaque) == session.profile


def test_lost_encryption_key_revokes_session_without_fallback_to_plaintext(identity):
    service, repository, authority, clock, _ = identity
    session = login(service)
    replacement = TokenVault(
        {"other": SecretStr(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())},
        active_key_id="other",
    )
    lost = SessionService(repository, authority, replacement, clock)
    with pytest.raises(SessionExpired):
        lost.resolve(session.opaque)
    assert stored(repository, session).encrypted_tokens is None


def test_copying_encrypted_tokens_between_database_rows_fails_closed(identity, engine):
    service, repository, _, _, _ = identity
    first, second = login(service), login(service)
    cipher = stored(repository, first).encrypted_tokens
    with engine.begin() as connection:
        connection.execute(
            text("SELECT set_config('app.session_hash', :hash, true)"),
            {"hash": session_hash(second.opaque)},
        )
        connection.execute(
            text("UPDATE auth_sessions SET encrypted_tokens=:cipher"), {"cipher": cipher}
        )
    with pytest.raises(SessionExpired):
        service.resolve(second.opaque)
    assert stored(repository, second).encrypted_tokens is None
    assert service.resolve(first.opaque) == first.profile


@pytest.mark.parametrize(
    "lifetime", [timedelta(), timedelta(minutes=4), timedelta(days=7, seconds=1)]
)
def test_session_lifetime_configuration_is_bounded(identity, lifetime):
    _, repository, authority, clock, key = identity
    with pytest.raises(ValueError):
        SessionService(
            repository,
            authority,
            TokenVault({"initial": key}, active_key_id="initial"),
            clock,
            lifetime=lifetime,
        )


@pytest.mark.parametrize("opaque", ["", "a" * 42, "a" * 44, "/" * 43])
def test_malformed_session_does_not_reach_the_database(identity, opaque):
    service, _, authority, _, _ = identity
    with pytest.raises(SessionExpired):
        service.resolve(SecretStr(opaque))
    assert authority.refreshes == 0
