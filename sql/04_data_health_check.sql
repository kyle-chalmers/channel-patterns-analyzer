-- ─── Data health check ───────────────────────────────────────
-- Per BUSINESS_RULES.md § "Data health expectations": surface the latest snapshot
-- date for every analytics table, plus the staleness in days. The analyzer must
-- include this in a Data Health section at the top of every report, flagging any
-- table more than 3 days stale.
--
-- Dataset name: bare `youtube_analytics.<table>` form; replace if your dataset
-- has a different name (see header of sql/01_latest_snapshot_overview.sql).
--
-- Timezone: Phoenix (America/Phoenix) is canonical for this analyzer; it is
-- the upstream youtube-bigquery-pipeline scheduler's timezone, so the staleness
-- window stays aligned with the actual ingest schedule. The four DATE_DIFF
-- calls below pass the Phoenix-tz string explicitly. See BUSINESS_RULES.md
-- § "Data health expectations".

SELECT
    'video_metadata' AS table_name,
    MAX(snapshot_date) AS latest_snapshot,
    DATE_DIFF(CURRENT_DATE("America/Phoenix"), MAX(snapshot_date), DAY) AS days_stale
FROM `youtube_analytics.video_metadata`

UNION ALL

SELECT
    'daily_video_stats' AS table_name,
    MAX(snapshot_date) AS latest_snapshot,
    DATE_DIFF(CURRENT_DATE("America/Phoenix"), MAX(snapshot_date), DAY) AS days_stale
FROM `youtube_analytics.daily_video_stats`

UNION ALL

SELECT
    'daily_video_analytics' AS table_name,
    MAX(snapshot_date) AS latest_snapshot,
    DATE_DIFF(CURRENT_DATE("America/Phoenix"), MAX(snapshot_date), DAY) AS days_stale
FROM `youtube_analytics.daily_video_analytics`

UNION ALL

SELECT
    'daily_traffic_sources' AS table_name,
    MAX(snapshot_date) AS latest_snapshot,
    DATE_DIFF(CURRENT_DATE("America/Phoenix"), MAX(snapshot_date), DAY) AS days_stale
FROM `youtube_analytics.daily_traffic_sources`

ORDER BY days_stale DESC;
