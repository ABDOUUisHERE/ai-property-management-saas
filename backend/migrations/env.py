import os

from alembic import context
from sqlalchemy import URL, create_engine
from sqlalchemy.pool import NullPool

from app.core.database import Base

url = URL.create(
    "postgresql+psycopg",
    username="pms_migrator",
    password=os.environ["PMS_MIGRATION_PASSWORD"],
    host=os.environ.get("PMS_DATABASE_HOST", "127.0.0.1"),
    port=int(os.environ.get("PMS_DATABASE_PORT", "15432")),
    database=os.environ.get("PMS_DATABASE_NAME", "property_management"),
)
engine = create_engine(url, poolclass=NullPool, hide_parameters=True)
try:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            connection.exec_driver_sql("SELECT pg_advisory_xact_lock(186732, 1)")
            context.run_migrations()
finally:
    engine.dispose()
