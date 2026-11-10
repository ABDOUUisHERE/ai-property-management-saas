#!/bin/sh
set -eu

psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=auth_password="$AUTH_DATABASE_PASSWORD" <<'SQL'
REVOKE CONNECT ON DATABASE auth FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- GoTrue's upstream migrations grant read access to a role named postgres.
-- In this isolated stack it is a compatibility grantee, not a login/admin account.
CREATE ROLE postgres NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
CREATE ROLE supabase_auth_admin LOGIN PASSWORD :'auth_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT CONNECT, CREATE ON DATABASE auth TO supabase_auth_admin;
GRANT USAGE ON SCHEMA public TO supabase_auth_admin;
CREATE SCHEMA auth AUTHORIZATION supabase_auth_admin;
ALTER ROLE supabase_auth_admin SET search_path = auth, public;
SQL
