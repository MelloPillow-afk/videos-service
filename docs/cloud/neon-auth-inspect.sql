-- Run with the intended runtime connection against the selected Neon branch.
-- Read-only metadata only: no user rows, tokens, or connection strings returned.
BEGIN READ ONLY;

SELECT table_name, column_name, data_type, udt_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'neon_auth'
ORDER BY table_name, ordinal_position;

SELECT n.nspname AS schema_name, c.relname AS relation_name,
       has_schema_privilege(current_user, n.oid, 'USAGE') AS schema_usage,
       has_table_privilege(current_user, c.oid, 'SELECT') AS can_select
FROM pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'neon_auth' AND c.relkind IN ('r', 'p', 'v')
ORDER BY c.relname;

ROLLBACK;
