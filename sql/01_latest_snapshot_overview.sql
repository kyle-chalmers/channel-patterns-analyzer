-- ─── Latest snapshot overview ─────────────────────────────────
-- One-row health check: latest COMMON snapshot date across both tables,
-- video counts by type, totals. Use this to confirm the upstream ingestion
-- is healthy before deeper analysis.
--
-- Dataset name: this query uses the bare `youtube_analytics.<table>` form
-- because the bq CLI resolves the project from your gcloud config. If your
-- dataset has a different name, replace `youtube_analytics` here (or have
-- the analyzer template `${BQ_DATASET}` when it runs).
--
-- Latest-common-snapshot logic: takes MIN(MAX(snapshot_date)) across both
-- source tables, so we never join a metadata row at a date where stats
-- haven't arrived yet (which would silently drop rows).

WITH latest_common AS (
    SELECT LEAST(
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.video_metadata`),
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.daily_video_stats`)
    ) AS snapshot_date
)
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
WHERE m.snapshot_date = (SELECT snapshot_date FROM latest_common)
GROUP BY m.snapshot_date;
