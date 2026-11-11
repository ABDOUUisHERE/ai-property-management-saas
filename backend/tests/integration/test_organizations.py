import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.bootstrap import create_app
from app.core.context import SystemClock
from app.core.database import make_engine
from app.core.errors import ApplicationError
from app.modules.identity.dependencies import authenticated_profile
from app.modules.identity.repository import IdentityRepository
from app.modules.organizations.repository import (
    OrganizationRepository,
    OrganizationTransaction,
    Role,
)
from app.modules.organizations.service import OrganizationService

pytestmark = pytest.mark.integration


@pytest.fixture
def organizations(engine):
    clock = SystemClock()
    identity = IdentityRepository(sessionmaker(engine))
    profiles = []
    for label in ("a", "b"):
        subject = uuid4()
        with identity.transaction(
            session_hash=secrets.token_hex(32), verified_subject=subject
        ) as tx:
            profiles.append(tx.upsert_profile(subject, f"{label}@example.test", clock.now()))
    repository = OrganizationRepository(sessionmaker(engine))
    return OrganizationService(repository, clock), repository, *profiles


def test_create_repeated_request_and_actor_scoped_lists(organizations, engine):
    service, _, a, b = organizations
    key = uuid4()
    first, created = service.create(a.id, "Demo Atlas", key)
    repeat, repeated = service.create(a.id, "Demo Atlas", key)
    foreign, _ = service.create(b.id, "Demo Atlas", key)
    assert first == repeat and created and not repeated
    assert first.id != foreign.id and first.role == Role.OWNER
    assert service.list(a.id) == [first]
    assert service.list(b.id) == [foreign]
    with pytest.raises(ApplicationError) as error:
        service.create(a.id, "Changed name", key)
    assert error.value.status == 409
    assert service.list(a.id) == [first]
    authorized = service.current(a.id, first.id)
    assert authorized.context.actor_id == a.id
    assert authorized.context.organization_id == first.id
    assert authorized.context.principal == "user"
    for actor, target in ((a.id, foreign.id), (b.id, first.id), (a.id, uuid4())):
        with pytest.raises(ApplicationError) as error:
            service.current(actor, target)
        assert error.value.status == 404
    assert engine.pool.checkedout() == 0


def test_two_selected_organizations_do_not_change_a_global_active_tenant(organizations):
    service, _, a, _ = organizations
    first, _ = service.create(a.id, "Demo first tab", uuid4())
    second, _ = service.create(a.id, "Demo second tab", uuid4())
    one = service.current(a.id, first.id)
    two = service.current(a.id, second.id)
    assert one.context.organization_id == first.id
    assert two.context.organization_id == second.id
    assert one.context.actor_id == two.context.actor_id == a.id
    assert service.current(a.id, first.id) == one


def test_concurrent_creation_uses_unique_key_across_distinct_connections(
    organizations, database, monkeypatch
):
    _, _, a, _ = organizations
    resources = [make_engine(database), make_engine(database)]
    barrier, key = Barrier(2), uuid4()
    original = OrganizationTransaction.create

    def synchronized(self, *args):
        barrier.wait(timeout=10)
        return original(self, *args)

    monkeypatch.setattr(OrganizationTransaction, "create", synchronized)
    services = [
        OrganizationService(OrganizationRepository(sessionmaker(e)), SystemClock())
        for e in resources
    ]
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda svc: svc.create(a.id, "Demo Atlas", key), services))
        assert results[0][0] == results[1][0]
        assert sorted(created for _, created in results) == [False, True]
        assert services[0].list(a.id) == [results[0][0]]
    finally:
        for resource in resources:
            resource.dispose()


def test_owner_insert_failure_rolls_back_the_organization(organizations, monkeypatch):
    service, _, a, _ = organizations

    def fail(self, *args):
        raise SQLAlchemyError("simulated owner insert failure")

    monkeypatch.setattr(OrganizationTransaction, "first_owner", fail)
    with pytest.raises(SQLAlchemyError):
        service.create(a.id, "Demo rollback", uuid4())
    assert service.list(a.id) == []


def test_database_cannot_commit_an_organization_without_its_first_member(organizations):
    _, repository, a, _ = organizations
    identifier = uuid4()
    with pytest.raises(DBAPIError):
        with repository.transaction(a.id, bootstrap_id=identifier) as tx:
            assert tx.create(identifier, "Demo incomplete", uuid4(), SystemClock().now())
    with repository.transaction(a.id) as tx:
        assert tx.list() == []


def test_bootstrap_cannot_add_an_owner_to_an_existing_organization(organizations):
    service, repository, a, b = organizations
    existing, _ = service.create(a.id, "Demo existing", uuid4())
    for actor in (a, b):
        with pytest.raises(DBAPIError):
            with repository.transaction(actor.id, bootstrap_id=existing.id) as tx:
                tx.first_owner(existing.id, SystemClock().now())
    assert service.list(b.id) == []


@pytest.mark.parametrize(
    "role,foreign,active",
    [
        ("manager", False, True),
        ("staff", False, True),
        ("owner", True, True),
        ("owner", False, False),
    ],
)
def test_first_member_policy_requires_the_active_owner_and_actual_creator(
    organizations, engine, role, foreign, active
):
    service, _, a, b = organizations
    identifier = uuid4()
    with pytest.raises(DBAPIError), engine.begin() as connection:
        connection.execute(
            text(
                "SELECT set_config('app.actor_id', :actor, true), "
                "set_config('app.bootstrap_organization', :org, true)"
            ),
            {"actor": str(a.id), "org": str(identifier)},
        )
        connection.execute(
            text(
                "INSERT INTO organizations (id,name,created_by,creation_key,created_at) "
                "VALUES (:id,'Demo denied',:actor,:key,now())"
            ),
            {"id": identifier, "actor": a.id, "key": uuid4()},
        )
        connection.execute(
            text(
                "INSERT INTO memberships (organization_id,user_id,role,active,created_at) "
                "VALUES (:org,:actor,:role,:active,now())"
            ),
            {"org": identifier, "actor": b.id if foreign else a.id, "role": role, "active": active},
        )
    assert service.list(a.id) == []


def test_duplicate_membership_is_rejected_in_the_bootstrap_transaction(organizations):
    service, repository, a, _ = organizations
    identifier = uuid4()
    with pytest.raises(DBAPIError), repository.transaction(a.id, bootstrap_id=identifier) as tx:
        tx.create(identifier, "Demo duplicate", uuid4(), SystemClock().now())
        tx.first_owner(identifier, SystemClock().now())
        tx.first_owner(identifier, SystemClock().now())
    assert service.list(a.id) == []


def test_runtime_denies_missing_context_and_foreign_rows_even_with_tenant_header(
    organizations, engine
):
    service, _, a, b = organizations
    first, _ = service.create(a.id, "Demo A", uuid4())
    foreign, _ = service.create(b.id, "Demo B", uuid4())
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT count(*) FROM organizations")) == 0
        assert connection.scalar(text("SELECT count(*) FROM memberships")) == 0
        connection.execute(
            text(
                "SELECT set_config('app.actor_id', :actor, true), "
                "set_config('app.organization_id', :tenant, true)"
            ),
            {"actor": str(a.id), "tenant": str(foreign.id)},
        )
        assert connection.execute(text("SELECT id FROM organizations")).scalars().all() == [
            first.id
        ]
        assert connection.execute(text("SELECT user_id FROM memberships")).scalars().all() == [a.id]
    with pytest.raises(DBAPIError), engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO organizations (id,name,created_by,creation_key,created_at) "
                "VALUES (:id,'Denied',:actor,:key,now())"
            ),
            {"id": uuid4(), "actor": a.id, "key": uuid4()},
        )
    with engine.begin() as connection:
        for key in ("app.actor_id", "app.organization_id", "app.bootstrap_organization"):
            assert (
                connection.scalar(
                    text("SELECT nullif(current_setting(:key,true), '')"), {"key": key}
                )
                is None
            )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE organizations SET created_by=:actor",
        "UPDATE memberships SET organization_id=:tenant",
        "UPDATE memberships SET role='owner'",
        "DELETE FROM memberships",
        "DELETE FROM organizations",
    ],
)
def test_runtime_cannot_rebind_or_remove_organization_membership(organizations, engine, statement):
    service, _, a, b = organizations
    first, _ = service.create(a.id, "Demo A", uuid4())
    foreign, _ = service.create(b.id, "Demo B", uuid4())
    with pytest.raises(DBAPIError), engine.begin() as connection:
        connection.execute(
            text("SELECT set_config('app.actor_id', :actor, true)"), {"actor": str(a.id)}
        )
        connection.execute(text(statement), {"actor": b.id, "tenant": foreign.id})
    assert service.current(a.id, first.id).organization == first


def privileged_engine(database, user, password):
    return create_engine(
        URL.create(
            "postgresql+psycopg",
            username=user,
            password=password,
            host=database.database_host,
            port=database.database_port,
            database=database.database_name,
        ),
        poolclass=NullPool,
        hide_parameters=True,
    )


def test_removed_membership_is_rechecked_and_pool_switches_actor(organizations, database):
    service, _, a, b = organizations
    first, _ = service.create(a.id, "Demo A", uuid4())
    foreign, _ = service.create(b.id, "Demo B", uuid4())
    assert service.current(a.id, first.id).organization == first
    admin = privileged_engine(database, "pms_admin", os.environ["PMS_TEST_ADMIN_PASSWORD"])
    try:
        with admin.begin() as connection:
            connection.execute(
                text(
                    "UPDATE memberships SET active=false "
                    "WHERE organization_id=:org AND user_id=:actor"
                ),
                {"org": first.id, "actor": a.id},
            )
    finally:
        admin.dispose()
    with pytest.raises(ApplicationError) as error:
        service.current(a.id, first.id)
    assert error.value.status == 404
    assert service.list(a.id) == []
    assert service.list(b.id) == [foreign]
    assert service.list(a.id) == []


def test_migration_owner_and_dispatcher_cannot_read_organizations(organizations, database):
    service, _, a, _ = organizations
    service.create(a.id, "Demo A", uuid4())
    migrator = privileged_engine(database, "pms_migrator", os.environ["PMS_MIGRATION_PASSWORD"])
    dispatcher = make_engine(database, dispatcher=True)
    try:
        with migrator.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.actor_id', :actor, true)"), {"actor": str(a.id)}
            )
            for table in ("organizations", "memberships"):
                assert connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0  # noqa: S608
        with pytest.raises(DBAPIError), dispatcher.begin() as connection:
            connection.execute(text("SELECT * FROM organizations"))
    finally:
        migrator.dispose()
        dispatcher.dispose()


def test_http_create_repeat_lists_and_cross_actor_selector(organizations, database):
    service, _, a, b = organizations
    app = create_app(database)
    actor = [a]
    app.dependency_overrides[authenticated_profile] = lambda: actor[0]
    with TestClient(app, base_url=database.browser_origin) as browser:
        app.state.organizations = service

        def signed():
            token = browser.get("/api/v1/auth/csrf")
            assert token.status_code == 200
            return {"Origin": database.browser_origin, "X-CSRF-Token": token.json()["csrf_token"]}

        body = {"name": "  Demo Atlas  ", "request_id": str(uuid4())}
        assert browser.post("/api/v1/organizations", json=body).status_code == 403
        created = browser.post("/api/v1/organizations", json=body, headers=signed())
        assert created.status_code == 201 and created.json()["role"] == "owner"
        assert created.json()["name"] == "Demo Atlas"
        identifier = created.json()["id"]
        assert browser.post("/api/v1/organizations", json=body, headers=signed()).status_code == 200
        assert browser.get("/api/v1/organizations").json() == [created.json()]
        selected = {"X-Organization-ID": identifier}
        assert (
            browser.get("/api/v1/organizations/current", headers=selected).json() == created.json()
        )
        assert browser.get("/api/v1/organizations/current").status_code == 422
        assert (
            browser.get(
                "/api/v1/organizations/current", headers={"X-Organization-ID": "bad"}
            ).status_code
            == 422
        )
        for extra in (
            {"role": "owner"},
            {"created_by": str(b.id)},
            {"organization_id": str(uuid4())},
        ):
            assert (
                browser.post(
                    "/api/v1/organizations", json={**body, **extra}, headers=signed()
                ).status_code
                == 422
            )
        assert created.headers["cache-control"] == "no-store"
        actor[0] = b
        assert browser.get("/api/v1/organizations").json() == []
        denied = browser.get("/api/v1/organizations/current", headers=selected)
        assert denied.status_code == 404 and identifier not in denied.text
