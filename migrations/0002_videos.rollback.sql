ALTER TABLE jobs DROP CONSTRAINT jobs_video_id_fkey;
ALTER TABLE jobs RENAME CONSTRAINT jobs_video_id_kind_key TO jobs_content_id_kind_key;
ALTER TABLE jobs RENAME COLUMN video_id TO content_id;
DROP TABLE videos;
