-- depends: 0001_jobs

-- Videos managed through the admin API. A set deleted_at hides the video from every
-- request; cleanup later removes its media and then the row, which removes its jobs.
CREATE TABLE videos (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    description text,
    status text NOT NULL DEFAULT 'CREATED'
        CHECK (status IN ('CREATED', 'UPLOADING', 'PROCESSING', 'READY', 'FAILED')),
    publication_status text NOT NULL DEFAULT 'DRAFT'
        CHECK (publication_status IN ('DRAFT', 'PUBLISHED')),
    published_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz,
    CHECK ((publication_status = 'PUBLISHED') = (published_at IS NOT NULL))
);

-- Every job belongs to a video, replacing 0001's generic content_id. The
-- (video_id, kind) unique index also serves the foreign key.
ALTER TABLE jobs RENAME COLUMN content_id TO video_id;
ALTER TABLE jobs RENAME CONSTRAINT jobs_content_id_kind_key TO jobs_video_id_kind_key;
ALTER TABLE jobs ADD CONSTRAINT jobs_video_id_fkey
    FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE;
