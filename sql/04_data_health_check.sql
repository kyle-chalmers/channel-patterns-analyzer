-- ─── Data health check ───────────────────────────────────────
-- Per BUSINESS_RULES.md §5: surface the latest snapshot date for every analytics
-- table, plus the staleness in days. The analyzer must include this in a Data
-- Health section at the top of every report, flagging any table more than 3 days stale.

SELECT
    'video_metadata' AS table_name,
    MAX(snapshot_date) AS latest_snapshot,
    DATE_DIFF(CURRENT_DATE(), MAX(snapshot_date), DAY) AS days_stale
FROM `youtube_analytics.video_metadata`

UNION ALL

SELECT
    'daily_video_stats' AS table_name,
    MAX(snapshot_date) AS latest_snapshot,
    DATE_DIFF(CURRENT_DATE(), MAX(snapshot_date), DAY) AS days_stale
FROM `youtube_analytics.daily_video_stats`

UNION ALL

SELECT
    'daily_video_analytics' AS table_name,
    MAX(snapshot_date) AS latest_snapshot,
    DATE_DIFF(CURRENT_DATE(), MAX(snapshot_date), DAY) AS days_stale
FROM `youtube_analytics.daily_video_analytics`

UNION ALL

SELECT
    'daily_traffic_sources' AS table_name,
    MAX(snapshot_date) AS latest_snapshot,
    DATE_DIFF(CURRENT_DATE(), MAX(snapshot_date), DAY) AS days_stale
FROM `youtube_analytics.daily_traffic_sources`

ORDER BY days_stale DESC;
