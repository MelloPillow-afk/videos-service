-- depends: 0002_videos

-- Each video list pages by keyset over its fixed sort order. Deleted videos never
-- appear in a list, and the catalog shows only ready, published videos.
CREATE INDEX videos_admin_list_idx ON videos (created_at DESC, id DESC)
    WHERE deleted_at IS NULL;
CREATE INDEX videos_catalog_list_idx ON videos (published_at DESC, id DESC)
    WHERE deleted_at IS NULL AND publication_status = 'PUBLISHED' AND status = 'READY';
