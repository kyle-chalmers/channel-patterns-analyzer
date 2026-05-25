-- ─── Data health check ───────────────────────────────────────
-- Per BUSINESS_RULES.md §5: surface the latest snapshot date for every analytics
-- table, plus the staleness in days. The analyzer must include this in a Data
-- Health section at the top of every report, flagging any table more than 3 days stale.
--
-- Dataset name: bare `youtube_analytics.<table>` form; replace if your dataset
-- has a different name (see header of sql/01_latest_snapshot_overview.sql).
--
-- Timezone: CURRENT_DATE() defaults to UTC in BigQuery. If your scheduling
-- timezone differs (e.g., America/Phoenix for the youtube-bigquery-pipeline
-- scheduler), use CURRENT_DATE("America/Phoenix") below to align the staleness
-- window with your actual ingest schedule.

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
