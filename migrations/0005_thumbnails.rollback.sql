DELETE FROM jobs WHERE kind = 'CUSTOM_THUMBNAIL_PROCESSING';
ALTER TABLE jobs DROP CONSTRAINT jobs_kind_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_kind_check CHECK (
    kind IN ('VIDEO_PROCESSING', 'THUMBNAIL_GENERATION', 'DELETION')
);
ALTER TABLE videos
    DROP COLUMN custom_thumbnail_prefix,
    DROP COLUMN thumbnail_upload_size_bytes,
    DROP COLUMN thumbnail_upload_key,
    DROP COLUMN thumbnail_upload_id;
ALTER TABLE videos RENAME COLUMN generated_thumbnail_prefix TO generated_thumbnail_key;
