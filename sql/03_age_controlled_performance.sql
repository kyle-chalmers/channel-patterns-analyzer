-- ─── Age-controlled performance comparison ───────────────────
-- Per BUSINESS_RULES.md §3: when comparing videos, control for age.
-- This query computes views per day since publish for each full-length video,
-- excluding any video published less than 14 days ago (low-confidence per the rule).

WITH base AS (
    SELECT
        m.video_id,
        m.title,
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
        AND DATE_DIFF(CURRENT_DATE(), DATE(m.published_at), DAY) >= 14
)
SELECT
    title,
    duration_formatted,
    days_since_published,
    view_count,
    SAFE_DIVIDE(view_count, days_since_published) AS views_per_day,
    SAFE_DIVIDE(like_count, view_count) * 100 AS like_rate_pct,
    SAFE_DIVIDE(comment_count, view_count) * 100 AS comment_rate_pct
FROM base
ORDER BY views_per_day DESC
LIMIT 20;
