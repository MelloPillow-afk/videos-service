-- depends: 0004_video_media

-- Thumbnails are rendered at several sizes under a key prefix. Earlier generated
-- thumbnails were one image, so their videos need processing again.
ALTER TABLE videos RENAME COLUMN generated_thumbnail_key TO generated_thumbnail_prefix;
UPDATE videos SET generated_thumbnail_prefix = NULL;

-- A custom thumbnail's current upload, like the source upload's columns; a new upload
-- URL replaces it. The worker sets custom_thumbnail_prefix once the upload is rendered.
ALTER TABLE videos
    ADD COLUMN thumbnail_upload_id uuid,
    ADD COLUMN thumbnail_upload_key text,
    ADD COLUMN thumbnail_upload_size_bytes bigint CHECK (thumbnail_upload_size_bytes > 0),
    ADD COLUMN custom_thumbnail_prefix text;

-- The custom thumbnail job belongs to the current thumbnail upload: replacing or
-- removing the upload deletes it, so (video_id, kind) stays unique.
ALTER TABLE jobs DROP CONSTRAINT jobs_kind_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_kind_check CHECK (
    kind IN ('VIDEO_PROCESSING', 'THUMBNAIL_GENERATION', 'CUSTOM_THUMBNAIL_PROCESSING', 'DELETION')
);
