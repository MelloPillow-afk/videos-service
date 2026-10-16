-- depends: 0002_worker_attempts
-- Keep bounded media execution diagnostics within the existing jobs table.
ALTER TABLE jobs ADD COLUMN execution_history jsonb NOT NULL DEFAULT '[]'::jsonb
    CHECK (jsonb_typeof(execution_history) = 'array');
