-- Runs once, as the bootstrap superuser, before anything connects.
--
-- Two roles, deliberately different:
--   cleared_owner  runs migrations. It may bypass row-level security, which is why the
--                  application never connects as it.
--   cleared_app    runs the application. Never a superuser, never BYPASSRLS.

alter role cleared_owner bypassrls;

create role cleared_app login password 'cleared_app' nosuperuser nobypassrls;
grant connect on database cleared_dev to cleared_app;

-- The test database lives on the same server; the harness drops and recreates its schema.
create database cleared_test owner cleared_owner;
grant connect on database cleared_test to cleared_app;

-- Grants for tables created later by migrations (which run as cleared_owner).
alter default privileges for role cleared_owner in schema public
  grant select, insert, update, delete on tables to cleared_app;
alter default privileges for role cleared_owner in schema public
  grant usage, select on sequences to cleared_app;
