"""Actor-scoped bootstrap and membership discovery, without a tenant bypass."""

from alembic import op

revision = "0004_organizations"
down_revision = "0003_account_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE organizations (
            id uuid PRIMARY KEY,
            name varchar(120) NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 120),
            created_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            creation_key uuid NOT NULL,
            created_at timestamptz NOT NULL,
            bootstrap_xid xid8 NOT NULL DEFAULT pg_current_xact_id(),
            CONSTRAINT uq_organizations_creation UNIQUE (created_by, creation_key)
        );
        CREATE TABLE memberships (
            organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            role varchar(10) NOT NULL CHECK (role IN ('owner', 'manager', 'staff')),
            active boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL,
            PRIMARY KEY (organization_id, user_id)
        );
        CREATE INDEX ix_memberships_actor ON memberships (user_id, organization_id) WHERE active;
        ALTER TABLE organizations ADD CONSTRAINT fk_organizations_first_member
            FOREIGN KEY (id, created_by) REFERENCES memberships(organization_id, user_id)
            DEFERRABLE INITIALLY DEFERRED;
        ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE organizations FORCE ROW LEVEL SECURITY;
        ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
        ALTER TABLE memberships FORCE ROW LEVEL SECURITY;
        REVOKE ALL ON organizations, memberships FROM pms_app;
        GRANT SELECT ON organizations, memberships TO pms_app;
        GRANT INSERT (id, name, created_by, creation_key, created_at) ON organizations TO pms_app;
        GRANT INSERT (organization_id, user_id, role, active, created_at) ON memberships TO pms_app;

        CREATE POLICY membership_self_read ON memberships FOR SELECT TO pms_app
            USING (user_id = nullif(current_setting('app.actor_id', true), '')::uuid);
        CREATE POLICY organization_read ON organizations FOR SELECT TO pms_app
            USING (
                EXISTS (SELECT 1 FROM memberships m WHERE m.organization_id=organizations.id
                        AND m.user_id=nullif(current_setting('app.actor_id', true), '')::uuid
                        AND m.active)
                OR (id=nullif(current_setting('app.bootstrap_organization', true), '')::uuid
                    AND created_by=nullif(current_setting('app.actor_id', true), '')::uuid
                    AND bootstrap_xid=pg_current_xact_id())
            );
        CREATE POLICY organization_bootstrap ON organizations FOR INSERT TO pms_app
            WITH CHECK (
                id=nullif(current_setting('app.bootstrap_organization', true), '')::uuid
                AND created_by=nullif(current_setting('app.actor_id', true), '')::uuid
                AND bootstrap_xid=pg_current_xact_id()
            );
        CREATE POLICY first_owner_bootstrap ON memberships FOR INSERT TO pms_app
            WITH CHECK (
                organization_id=
                    nullif(current_setting('app.bootstrap_organization', true), '')::uuid
                AND user_id=nullif(current_setting('app.actor_id', true), '')::uuid
                AND role='owner' AND active
                AND EXISTS (SELECT 1 FROM organizations o WHERE o.id=memberships.organization_id
                    AND o.created_by=memberships.user_id AND o.bootstrap_xid=pg_current_xact_id())
            );
    """)


def downgrade() -> None:
    # Destructive: restoration in a separate database, not a live downgrade.
    op.execute("ALTER TABLE organizations DROP CONSTRAINT fk_organizations_first_member")
    op.execute("DROP POLICY organization_read ON organizations")
    op.execute("DROP TABLE memberships")
    op.execute("DROP TABLE organizations")
