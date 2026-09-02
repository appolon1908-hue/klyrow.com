BEGIN;

-- The official Postgres image keeps its bootstrap role as the cluster owner.
-- Application processes use this separate, fixed, non-owner login instead.
DO $klyrow$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'klyrow_runtime') THEN
    CREATE ROLE klyrow_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
      NOREPLICATION NOBYPASSRLS;
  END IF;
END
$klyrow$;

DO $klyrow$
BEGIN
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO klyrow_runtime', current_database());
END
$klyrow$;
GRANT USAGE ON SCHEMA public TO klyrow_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO klyrow_runtime;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO klyrow_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO klyrow_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO klyrow_runtime;

COMMIT;
