-- Three application tables; Neon Auth owns identities and roles.
CREATE TABLE videos (
    id uuid PRIMARY KEY,
    title text NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    description text,
    status text NOT NULL DEFAULT 'CREATED'
        CHECK (status IN ('CREATED','UPLOADING','QUEUED','PROCESSING','READY','FAILED','DELETING')),
    publication_status text NOT NULL DEFAULT 'DRAFT' CHECK (publication_status IN ('DRAFT','PUBLISHED')),
    source_key text,
    source_validated boolean NOT NULL DEFAULT false,
    playback_key text,
    size_bytes bigint CHECK (size_bytes > 0),
    duration_seconds double precision CHECK (duration_seconds >= 0),
    width integer CHECK (width > 0),
    height integer CHECK (height > 0),
    generated_thumbnail_status text NOT NULL DEFAULT 'PENDING'
        CHECK (generated_thumbnail_status IN ('PENDING','READY','FAILED')),
    generated_thumbnail_key text,
    custom_thumbnail_key text,
    processing_error_code text,
    processing_error_message text,
    published_at timestamptz,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CHECK ((publication_status = 'PUBLISHED') = (published_at IS NOT NULL))
);
CREATE TABLE upload_attempts (
    id uuid PRIMARY KEY,
    video_id uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('SOURCE','THUMBNAIL')),
    object_key text NOT NULL UNIQUE,
    declared_size_bytes bigint NOT NULL CHECK (declared_size_bytes > 0),
    content_type text NOT NULL,
    expires_at timestamptz NOT NULL,
    is_current boolean NOT NULL DEFAULT true,
    state text NOT NULL DEFAULT 'PENDING' CHECK (state IN ('PENDING','ACCEPTED','SUPERSEDED','REMOVED')),
    accepted_at timestamptz,
    created_at timestamptz NOT NULL,
    CHECK (state <> 'ACCEPTED' OR accepted_at IS NOT NULL)
);
CREATE UNIQUE INDEX upload_attempts_current ON upload_attempts(video_id, kind) WHERE is_current;
CREATE TABLE jobs (
    id uuid PRIMARY KEY,
    video_id uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('VIDEO','THUMBNAIL','DELETION')),
    is_current boolean NOT NULL DEFAULT true,
    state text NOT NULL DEFAULT 'RECORDED'
        CHECK (state IN ('RECORDED','LAUNCHED','RUNNING','SUCCEEDED','FAILED','LAUNCH_FAILED')),
    execution_attempts integer NOT NULL DEFAULT 0 CHECK (execution_attempts >= 0),
    output_prefix text NOT NULL UNIQUE,
    execution_reference text,
    error_code text,
    error_message text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);
CREATE UNIQUE INDEX jobs_current ON jobs(video_id, kind) WHERE is_current;
CREATE INDEX videos_library_order ON videos(created_at DESC, id DESC);
