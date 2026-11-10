"""Durable outbox, bounded dispatcher capability and tenant-scoped receipts."""

from alembic import op

revision = "0001_outbox"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE outbox_events (
            id uuid PRIMARY KEY,
            organization_id uuid NOT NULL,
            event_type text NOT NULL,
            payload jsonb NOT NULL,
            occurred_at timestamptz NOT NULL,
            CONSTRAINT uq_outbox_events_organization_id UNIQUE (organization_id, id)
        );
        CREATE TABLE outbox_deliveries (
            organization_id uuid NOT NULL,
            event_id uuid NOT NULL,
            consumer text NOT NULL,
            attempts integer NOT NULL DEFAULT 0,
            next_attempt_at timestamptz NOT NULL DEFAULT now(),
            completed_at timestamptz,
            failed_at timestamptz,
            error_code text,
            CONSTRAINT pk_outbox_deliveries PRIMARY KEY (organization_id, event_id, consumer),
            CONSTRAINT fk_outbox_deliveries_event FOREIGN KEY (organization_id, event_id)
                REFERENCES outbox_events (organization_id, id) ON DELETE CASCADE,
            CONSTRAINT ck_outbox_deliveries_attempts CHECK (attempts >= 0)
        );
        CREATE INDEX ix_outbox_deliveries_due ON outbox_deliveries (next_attempt_at)
            WHERE completed_at IS NULL AND failed_at IS NULL;
        CREATE TABLE consumer_receipts (
            organization_id uuid NOT NULL,
            event_id uuid NOT NULL,
            consumer text NOT NULL,
            consumed_at timestamptz NOT NULL,
            CONSTRAINT pk_consumer_receipts PRIMARY KEY (organization_id, event_id, consumer),
            CONSTRAINT fk_consumer_receipts_delivery
                FOREIGN KEY (organization_id, event_id, consumer)
                REFERENCES outbox_deliveries (organization_id, event_id, consumer)
        );
    """)
    for table in ("outbox_events", "outbox_deliveries", "consumer_receipts"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_scope ON {table} TO pms_app
            USING (organization_id = nullif(current_setting('app.organization_id', true), '')::uuid)
            WITH CHECK (
                organization_id = nullif(current_setting('app.organization_id', true), '')::uuid
            )
        """)
        op.execute(f"REVOKE ALL ON {table} FROM pms_app")
    op.execute("GRANT SELECT, INSERT ON outbox_events, consumer_receipts TO pms_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON outbox_deliveries TO pms_app")
    # This role cannot read payloads or any business table. It sees routing metadata only.
    op.execute("GRANT USAGE ON SCHEMA public TO pms_dispatcher")
    op.execute("GRANT SELECT, UPDATE ON outbox_deliveries TO pms_dispatcher")
    op.execute(
        "CREATE POLICY dispatch_scope ON outbox_deliveries TO pms_dispatcher "
        "USING (true) WITH CHECK (true)"
    )
    op.execute("REVOKE ALL ON alembic_version FROM pms_app")
    op.execute("GRANT SELECT ON alembic_version TO pms_app")


def downgrade() -> None:
    # Local/dev only: this removes durable jobs and receipts. Back up before invoking.
    for table in ("consumer_receipts", "outbox_deliveries", "outbox_events"):
        op.execute(f"DROP TABLE {table}")
