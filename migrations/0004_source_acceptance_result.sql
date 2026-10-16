-- depends: 0001_video_library
-- Preserve the result of accepted completion independently of later retries.
ALTER TABLE upload_attempts ADD COLUMN processing_job_id uuid REFERENCES jobs(id);
UPDATE upload_attempts SET processing_job_id = (
    SELECT id FROM jobs WHERE jobs.video_id = upload_attempts.video_id AND kind = 'VIDEO'
    ORDER BY created_at, id LIMIT 1
) WHERE kind = 'SOURCE' AND state = 'ACCEPTED';
ALTER TABLE upload_attempts ADD CONSTRAINT source_accepted_result
    CHECK (kind <> 'SOURCE' OR state <> 'ACCEPTED' OR processing_job_id IS NOT NULL);
