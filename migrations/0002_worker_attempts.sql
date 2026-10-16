-- depends: 0001_video_library
-- Worker claims and a finite object manifest stay in the existing jobs table.
ALTER TABLE jobs ADD COLUMN claim_token uuid;
ALTER TABLE jobs ADD COLUMN output_keys jsonb NOT NULL DEFAULT '[]'::jsonb
    CHECK (jsonb_typeof(output_keys) = 'array');
