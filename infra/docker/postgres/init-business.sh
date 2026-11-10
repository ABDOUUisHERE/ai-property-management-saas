#!/bin/sh
set -eu

# The official Postgres entrypoint runs non-executable .sh files by sourcing them.
psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=migration_password="$DATABASE_MIGRATION_PASSWORD" \
  --set=runtime_password="$DATABASE_RUNTIME_PASSWORD" <<'SQL'
REVOKE CONNECT ON DATABASE property_management FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE ROLE pms_migrator LOGIN PASSWORD :'migration_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
CREATE ROLE pms_app LOGIN PASSWORD :'runtime_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT CONNECT, CREATE ON DATABASE property_management TO pms_migrator;
GRANT CONNECT ON DATABASE property_management TO pms_app;
ALTER SCHEMA public OWNER TO pms_migrator;
GRANT USAGE ON SCHEMA public TO pms_app;
ALTER DEFAULT PRIVILEGES FOR ROLE pms_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO pms_app;
ALTER DEFAULT PRIVILEGES FOR ROLE pms_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO pms_app;
SQL
