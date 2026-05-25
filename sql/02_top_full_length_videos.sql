-- ─── Top full-length videos by views (latest snapshot) ───────
-- The analyzer's "what's working" foundation.
-- Filters out shorts. Ranks full-length videos by cumulative views with engagement.
-- Apply the age-control rule (BUSINESS_RULES.md §3) downstream — this is raw data.
--
-- Dataset name: bare `youtube_analytics.<table>` form; bq CLI resolves project from
-- your gcloud config. Replace `youtube_analytics` if your dataset has a different name.
--
-- Note on duration_formatted: this column is a custom field produced by the
-- youtube-bigquery-pipeline ingest job, not a native YouTube API field. If your own
-- pipeline lands `duration_seconds` only, derive `duration_formatted` in the SELECT
-- (e.g., FORMAT_TIME(TIME_ADD(TIME '00:00:00', INTERVAL duration_seconds SECOND), '%M:%S'))
-- or drop the column.

SELECT
    m.title,
    m.video_type,
    m.duration_formatted,
    m.published_at,
    DATE_DIFF(CURRENT_DATE('America/Phoenix'), DATE(m.published_at), DAY) AS days_since_published,
    s.view_count,
    s.like_count,
    s.comment_count
FROM `youtube_analytics.video_metadata` m
JOIN `youtube_analytics.daily_video_stats` s
    USING (video_id, snapshot_date)
WHERE m.snapshot_date = (
    SELECT MAX(snapshot_date) FROM `youtube_analytics.video_metadata`
)
    AND m.video_type = 'full_length'
ORDER BY s.view_count DESC
LIMIT 20;
