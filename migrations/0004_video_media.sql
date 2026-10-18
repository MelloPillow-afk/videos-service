-- depends: 0003_video_listing

-- Media a video gathers from upload and processing. upload_id names the current
-- upload; requesting a new upload URL replaces it, so older uploads cannot complete.
-- size_bytes is declared with the upload URL and replaced by the stored size on
-- completion. Workers set the output keys and duration.
ALTER TABLE videos
    ADD COLUMN upload_id uuid,
    ADD COLUMN source_key text,
    ADD COLUMN size_bytes bigint CHECK (size_bytes > 0),
    ADD COLUMN duration_seconds numeric CHECK (duration_seconds >= 0),
    ADD COLUMN playback_key text,
    ADD COLUMN generated_thumbnail_key text;
