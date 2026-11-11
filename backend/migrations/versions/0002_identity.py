"""Identity-global profiles and capability-scoped, revocable facade sessions."""

from alembic import op

revision = "0002_identity"
down_revision = "0001_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE users (
            id uuid PRIMARY KEY,
            auth_subject uuid NOT NULL UNIQUE,
            email varchar(320) NOT NULL,
            created_at timestamptz NOT NULL,
            CONSTRAINT uq_users_id_subject UNIQUE (id, auth_subject),
            CONSTRAINT ck_users_email_length CHECK (length(email) >= 3)
        );
        CREATE TABLE auth_sessions (
            session_hash varchar(64) PRIMARY KEY,
            user_id uuid NOT NULL,
            auth_subject uuid NOT NULL,
            provider_session_id uuid NOT NULL,
            encrypted_tokens text,
            access_expires_at timestamptz NOT NULL,
            created_at timestamptz NOT NULL,
            absolute_expires_at timestamptz NOT NULL,
            version integer NOT NULL DEFAULT 0,
            refresh_owner uuid,
            refresh_deadline timestamptz,
            revoked_at timestamptz,
            CONSTRAINT fk_auth_sessions_user FOREIGN KEY (user_id, auth_subject)
                REFERENCES users (id, auth_subject) ON DELETE RESTRICT,
            CONSTRAINT ck_auth_sessions_hash CHECK (session_hash ~ '^[a-f0-9]{64}$'),
            CONSTRAINT ck_auth_sessions_version CHECK (version >= 0),
            CONSTRAINT ck_auth_sessions_lifetime CHECK (
                absolute_expires_at > created_at
                AND absolute_expires_at <= created_at + interval '7 days'
            ),
            CONSTRAINT ck_auth_sessions_lease CHECK (
                (refresh_owner IS NULL) = (refresh_deadline IS NULL)
            ),
            CONSTRAINT ck_auth_sessions_revocation CHECK (
                (revoked_at IS NULL) = (encrypted_tokens IS NOT NULL)
                AND (revoked_at IS NULL OR refresh_owner IS NULL)
            )
        );
        CREATE INDEX ix_auth_sessions_expiry ON auth_sessions (absolute_expires_at);
        ALTER TABLE users ENABLE ROW LEVEL SECURITY;
        ALTER TABLE users FORCE ROW LEVEL SECURITY;
        ALTER TABLE auth_sessions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE auth_sessions FORCE ROW LEVEL SECURITY;
        REVOKE ALL ON users, auth_sessions FROM pms_app;
        GRANT SELECT, INSERT ON users, auth_sessions TO pms_app;
        GRANT UPDATE (email) ON users TO pms_app;
        GRANT UPDATE (encrypted_tokens, access_expires_at, version, refresh_owner,
                      refresh_deadline, revoked_at) ON auth_sessions TO pms_app;

        CREATE POLICY session_read ON auth_sessions FOR SELECT TO pms_app
            USING (session_hash = nullif(current_setting('app.session_hash', true), ''));
        CREATE POLICY session_insert ON auth_sessions FOR INSERT TO pms_app
            WITH CHECK (
                auth_subject = nullif(current_setting('app.auth_subject', true), '')::uuid
                AND session_hash = nullif(current_setting('app.session_hash', true), '')
            );
        CREATE POLICY session_update ON auth_sessions FOR UPDATE TO pms_app
            USING (session_hash = nullif(current_setting('app.session_hash', true), ''))
            WITH CHECK (session_hash = nullif(current_setting('app.session_hash', true), ''));

        CREATE POLICY profile_read ON users FOR SELECT TO pms_app
            USING (
                auth_subject = nullif(current_setting('app.auth_subject', true), '')::uuid
                OR EXISTS (
                    SELECT 1 FROM auth_sessions s WHERE s.user_id = users.id
                    AND s.revoked_at IS NULL AND s.absolute_expires_at > current_timestamp
                )
            );
        CREATE POLICY profile_insert ON users FOR INSERT TO pms_app
            WITH CHECK (auth_subject = nullif(current_setting('app.auth_subject', true), '')::uuid);
        CREATE POLICY profile_update ON users FOR UPDATE TO pms_app
            USING (auth_subject = nullif(current_setting('app.auth_subject', true), '')::uuid)
            WITH CHECK (auth_subject = nullif(current_setting('app.auth_subject', true), '')::uuid);
    """)


def downgrade() -> None:
    # Destructive: use a restored database for rollback. Test only on disposable DBs.
    op.execute("DROP POLICY profile_read ON users")
    op.execute("DROP TABLE auth_sessions")
    op.execute("DROP TABLE users")
