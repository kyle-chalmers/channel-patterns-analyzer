-- ─── Age-controlled performance comparison ───────────────────
-- Per BUSINESS_RULES.md §3: when comparing videos, control for age.
-- This query computes views per day since publish for each full-length video,
-- excluding any video published less than 14 days ago (low-confidence per the rule).
--
-- Dataset name: bare `youtube_analytics.<table>` form; replace if your dataset
-- has a different name (see header of sql/01_latest_snapshot_overview.sql).
--
-- IMPORTANT: `views_per_day_since_publish_proxy` is a PROXY for the strict
-- first-30-day normalization required by BUSINESS_RULES.md §3 — it averages
-- across the entire post-publish window rather than computing views in the
-- first 30 days specifically. For the strict rule, compute the delta between
-- the snapshot at publish + 30 days vs. snapshot at publish (requires
-- per-snapshot row history). Use this proxy when that history is unavailable
-- or when a relative ranking is good enough; label results as a proxy in
-- the report.

WITH base AS (
    SELECT
        m.video_id,
        m.title,
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
        AND DATE_DIFF(CURRENT_DATE('America/Phoenix'), DATE(m.published_at), DAY) >= 14
)
SELECT
    title,
    duration_formatted,
    days_since_published,
    view_count,
    SAFE_DIVIDE(view_count, days_since_published) AS views_per_day_since_publish_proxy,
    SAFE_DIVIDE(like_count, view_count) * 100 AS like_rate_pct,
    SAFE_DIVIDE(comment_count, view_count) * 100 AS comment_rate_pct
FROM base
ORDER BY views_per_day_since_publish_proxy DESC
LIMIT 20;
