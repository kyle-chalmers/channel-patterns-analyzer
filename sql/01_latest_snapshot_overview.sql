-- ─── Latest snapshot overview ─────────────────────────────────
-- One-row health check: latest snapshot date, video counts by type, totals.
-- Use this to confirm the upstream ingestion is healthy before deeper analysis.

SELECT
    m.snapshot_date AS latest_snapshot,
    COUNT(*) AS total_videos,
    COUNTIF(m.video_type = 'full_length') AS full_length_count,
    COUNTIF(m.video_type = 'short') AS shorts_count,
    SUM(s.view_count) AS total_views,
    SUM(s.like_count) AS total_likes,
    SUM(s.comment_count) AS total_comments
FROM `youtube_analytics.video_metadata` m
JOIN `youtube_analytics.daily_video_stats` s
    USING (video_id, snapshot_date)
WHERE m.snapshot_date = (
    SELECT MAX(snapshot_date) FROM `youtube_analytics.video_metadata`
)
GROUP BY m.snapshot_date;
