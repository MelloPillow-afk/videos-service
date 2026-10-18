ALTER TABLE videos
    DROP COLUMN generated_thumbnail_key,
    DROP COLUMN playback_key,
    DROP COLUMN duration_seconds,
    DROP COLUMN size_bytes,
    DROP COLUMN source_key,
    DROP COLUMN upload_id;
