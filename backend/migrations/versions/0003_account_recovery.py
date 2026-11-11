"""Per-subject recovery barrier; no global access to session ciphertext."""

from alembic import op

revision = "0003_account_recovery"
down_revision = "0002_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users ADD COLUMN sessions_valid_after timestamptz;
        ALTER TABLE users ADD COLUMN recovery_owner uuid;
        ALTER TABLE users ADD COLUMN recovery_deadline timestamptz;
        ALTER TABLE users ADD CONSTRAINT ck_users_recovery_lease CHECK (
            (recovery_owner IS NULL) = (recovery_deadline IS NULL)
            AND (recovery_owner IS NULL OR sessions_valid_after IS NOT NULL)
        );
        GRANT UPDATE (sessions_valid_after, recovery_owner, recovery_deadline)
            ON users TO pms_app;
    """)


def downgrade() -> None:
    # Security rollback can restore old sessions. Restore a snapshot and rotate
    # all local sessions before running older application code; never downgrade live.
    op.execute("""
        ALTER TABLE users DROP CONSTRAINT ck_users_recovery_lease;
        ALTER TABLE users DROP COLUMN recovery_deadline;
        ALTER TABLE users DROP COLUMN recovery_owner;
        ALTER TABLE users DROP COLUMN sessions_valid_after;
    """)
