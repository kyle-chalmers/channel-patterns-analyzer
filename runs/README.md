# Runs — audit trail

One folder per analyzer run, named by **run date**. Each folder is a self-contained record of what the analyzer saw and did that day.

```
runs/
  2026-05-24/
    summary.json           ← run metadata (see schema below)
    queries/               ← raw JSON dump of each SQL result
      01_data_health.json
      02_top_videos.json
      03_age_controlled.json
      04_traffic_sources.json
    report.md              ← mirror of reports/2026-05-24.md, kept here for a self-contained folder
```

## Why this exists

When a Notion report from three months ago says something surprising, opening `runs/{that-date}/` shows:

- which BigQuery snapshot dates were live at the time,
- what the query results actually were (row counts and raw rows),
- whether anything errored,
- which report file was published.

That's the difference between "the analyzer said it" and "the analyzer said it and here's why."

The dataset is small enough (~23 videos across 4 tables) that committing raw query results is cheap and worth it.

## `summary.json` schema

```json
{
  "run_date": "2026-05-24",
  "run_started_at": "2026-05-24T20:00:00-07:00",
  "run_finished_at": "2026-05-24T20:04:32-07:00",
  "data_source": "bigquery",
  "transport": "bq_cli",
  "bq_project": "<project-id>",
  "bq_dataset": "youtube_analytics",
  "snapshot_dates": {
    "video_metadata": "2026-05-23",
    "daily_video_stats": "2026-05-23",
    "daily_video_analytics": "2026-05-22",
    "daily_traffic_sources": "2026-05-23"
  },
  "stale_tables": ["daily_video_analytics (2 days)"],
  "video_count_full_length": 24,
  "queries_run": [
    {"file": "01_data_health.sql", "rows": 4, "ms": 412},
    {"file": "02_top_videos.sql", "rows": 24, "ms": 387}
  ],
  "report_path": "reports/2026-05-24.md",
  "notion_write_ok": true,
  "notion_page_id": "<page-id>",
  "notion_url": "https://www.notion.so/Weekly-report-2026-05-24-<shortid>",
  "prior_reports_consulted": ["2026-05-18", "2026-05-11", "2026-05-04"],
  "errors": []
}
```

Always write `summary.json`, even on failure. A failed run with `errors: [...]` is more useful than a missing folder.

`transport` is `"bq_cli"` when the run used the local `bq` CLI and `"bq_mcp"` when it used the BigQuery MCP tool surface; the recipe probes available tools at runtime (per CONTEXT.md D-03) and records which one fired. `notion_url` is populated when `notion_write_ok` is true, so post-mortems can jump straight to the published page without rebuilding the URL from `notion_page_id`.

`prior_reports_consulted` is the list of dates of `reports/{YYYY-MM-DD}.md` files the analyzer read during the prior-report calibration step at draft time (per CLAUDE.md § "Report structure" and `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md` D-10). The array MAY be empty if fewer than three prior reports exist or none were consulted (e.g., the first ever run). The recipe filters out today's `run_date` before selecting the three most recent dates, so this list never includes today (same-day retries belong to "this run", not the calibration archive). Phase 2 Plan 02-03 adds a `voice_audit` field for the self-audit step; it is not part of the Phase 2 Plan 02-02 schema.

## Related

- `reports/` — the human-readable archive (same content as `report.md` here, gathered in one place for browsing).
- `docs/runbook.md` — what to do when a run errors.
- `CHANGELOG.md` — when the analyzer's behavior or rules change.
