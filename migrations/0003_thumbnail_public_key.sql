-- depends: 0001_video_library
-- Register each finite public image key before a storage write can begin.
ALTER TABLE upload_attempts ADD COLUMN public_object_key text;
CREATE UNIQUE INDEX upload_attempts_public_object_key
ON upload_attempts(public_object_key) WHERE public_object_key IS NOT NULL;
