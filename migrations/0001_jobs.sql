-- Background work for any content. content_id is generic, so it has no foreign key;
-- the owning resource deletes its jobs explicitly. Retries are left to Cloud Run,
-- so each content has at most one job of each kind.
CREATE TABLE jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id uuid NOT NULL,
    kind text NOT NULL
        CHECK (kind IN ('VIDEO_PROCESSING', 'THUMBNAIL_GENERATION', 'DELETION')),
    status text NOT NULL DEFAULT 'QUEUED'
        CHECK (status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED')),
    message text CHECK (message IS NULL OR status = 'FAILED'),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (content_id, kind)
);
