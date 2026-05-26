-- ─── Top full-length videos by views (latest snapshot) ───────
-- The analyzer's "what's working" foundation.
-- Filters out shorts. Ranks full-length videos by cumulative views with engagement.
-- Apply the age-control rule (CLAUDE.md § "Age control is non-negotiable") downstream — this is raw data.
--
-- Dataset name: bare `youtube_analytics.<table>` form; bq CLI resolves project from
-- your gcloud config. Replace `youtube_analytics` if your dataset has a different name.
--
-- Timezone: CURRENT_DATE("America/Phoenix") aligns date math with the upstream
-- youtube-bigquery-pipeline scheduler. See BUSINESS_RULES.md § "Data health expectations".
--
-- Latest-common-snapshot logic: takes MIN(MAX(snapshot_date)) across video_metadata
-- and daily_video_stats so we never join a metadata row at a date where stats
-- haven't arrived yet (which would silently drop rows). Scope is the two joined
-- tables only; extension to all four analytics tables is deferred (see sql/01
-- and Phase 2 D-06).
--
-- NULL-guard: if either source table is empty, MAX(snapshot_date) returns NULL
-- and LEAST(NULL, X) returns NULL, so the equality filter
-- `m.snapshot_date = NULL` never matches and the query returns zero rows. That
-- is indistinguishable from "no full-length videos exist" at the recipe layer.
-- The recipe's Step 2 data-health check is the primary guard (it routes empty
-- source tables to a STOP before this query runs), but the IS NOT NULL guard
-- below makes the intent explicit at the SQL layer too, so the failure mode
-- doesn't reappear if the recipe order changes.
--
-- Note on duration_formatted: this column is a custom field produced by the
-- youtube-bigquery-pipeline ingest job, not a native YouTube API field. If your own
-- pipeline lands `duration_seconds` only, derive `duration_formatted` in the SELECT
-- (e.g., FORMAT_TIME(TIME_ADD(TIME '00:00:00', INTERVAL duration_seconds SECOND), '%M:%S'))
-- or drop the column.

WITH latest_common AS (
    SELECT LEAST(
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.video_metadata`),
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.daily_video_stats`)
    ) AS snapshot_date
)
SELECT
    m.title,
    m.video_type,
    m.duration_formatted,
    m.published_at,
    DATE_DIFF(CURRENT_DATE("America/Phoenix"), DATE(m.published_at), DAY) AS days_since_published,
    s.view_count,
    s.like_count,
    s.comment_count
FROM `youtube_analytics.video_metadata` m
JOIN `youtube_analytics.daily_video_stats` s
    USING (video_id, snapshot_date)
WHERE (SELECT snapshot_date FROM latest_common) IS NOT NULL
    AND m.snapshot_date = (SELECT snapshot_date FROM latest_common)
    AND m.video_type = 'full_length'
ORDER BY s.view_count DESC;
