-- ─── Top full-length videos by views (latest snapshot) ───────
-- The analyzer's "what's working" foundation.
-- Filters out shorts. Ranks full-length videos by cumulative views with engagement.
-- Apply the age-control rule (BUSINESS_RULES.md §3) downstream — this is raw data.

SELECT
    m.title,
    m.video_type,
    m.duration_formatted,
    m.published_at,
    DATE_DIFF(CURRENT_DATE(), DATE(m.published_at), DAY) AS days_since_published,
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
