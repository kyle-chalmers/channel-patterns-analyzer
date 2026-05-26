# Runs — audit trail

One folder per analyzer run, named by **run date**. Each folder is a self-contained record of what the analyzer saw and did that day.

```
runs/
  2026-05-24/
    summary.json           ← run metadata (see schema below)
    queries/               ← raw JSON dump of each SQL result
      data_health.json              ← from sql/04_data_health_check.sql
      top_full_length_videos.json   ← from sql/02_top_full_length_videos.sql
      eligible_video_count.json     ← from the recipe-inline eligible-count SQL (Step 5)
    report.md              ← mirror of reports/2026-05-24.md, kept here for a self-contained folder
```

The query JSON filenames are the recipe's choice (they describe the result, not the SQL file); the `queries_run[].file` field in `summary.json` points at the SQL source file under `sql/`. Phase 1 runs the three queries above. Phase 2 and later add new query outputs in this same folder; each new output is documented as part of the change that introduces it.

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
    {"file": "sql/04_data_health_check.sql", "rows": 4, "ms": 412},
    {"file": "sql/02_top_full_length_videos.sql", "rows": 24, "ms": 387},
    {"file": "eligible_video_count (recipe-inline)", "rows": 1, "ms": 198}
  ],
  "report_path": "reports/2026-05-24.md",
  "notion_write_ok": true,
  "notion_page_id": "<page-id>",
  "notion_url": "https://www.notion.so/Weekly-report-2026-05-24-<shortid>",
  "prior_reports_consulted": ["2026-05-18", "2026-05-11", "2026-05-04"],
  "voice_audit": {
    "checks_passed": [
      "six_sections_in_order",
      "empty_sections_render_with_explicit_body",
      "stale_table_disclaimers_present",
      "age_control_enforced",
      "cross_age_window_labeled",
      "trending_claims_have_minimum_age",
      "confidence_labels_present",
      "confidence_n_matches_comparison_set",
      "confidence_thresholds_correct",
      "no_em_dashes",
      "no_en_dashes_as_punctuation",
      "no_banned_vocab",
      "no_formulaic_openers",
      "first_person_plural_where_it_fits",
      "no_prior_report_citation",
      "multi_week_claims_self_contained",
      "numbers_match_underlying_query_results"
    ],
    "fixes_applied": [
      {"section": "Patterns worth watching", "fix": "Replaced em dash with comma in framing of tool-tutorials trend"},
      {"section": "What is working", "fix": "Added (standard confidence, n=18) parenthetical to median-views claim"}
    ]
  },
  "errors": []
}
```

Always write `summary.json`, even on failure. A failed run with `errors: [...]` is more useful than a missing folder.

`transport` is `"bq_cli"` when the run used the local `bq` CLI and `"bq_mcp"` when it used the BigQuery MCP tool surface; the recipe probes available tools at runtime (per CONTEXT.md D-03) and records which one fired. `notion_url` is populated when `notion_write_ok` is true, so post-mortems can jump straight to the published page without rebuilding the URL from `notion_page_id`.

`prior_reports_consulted` is the list of dates of `reports/{YYYY-MM-DD}.md` files the analyzer read during the prior-report calibration step at draft time (per CLAUDE.md § "Report structure" and `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md` D-10). The array MAY be empty if fewer than three prior reports exist or none were consulted (e.g., the first ever run). The recipe filters out today's `run_date` before selecting the three most recent dates, so this list never includes today (same-day retries belong to "this run", not the calibration archive).

`voice_audit` is the audit trail of the self-audit step (Step 7 in `.claude/commands/run-analyzer.md`), added by Phase 2 Plan 02-03 (D-01 Layer 2). The step is a copy-into-response checklist the analyzer walks against the assembled draft before invoking `write-notion-report`; the publish gate is explicit, so the Skill is not invoked while any item remains unticked.

- `checks_passed` is the list of canonical check identifiers (snake-case names, defined in the recipe's Step 7) that the analyzer ticked through cleanly. The example above lists the full 17-identifier set in the same order the recipe documents them (`six_sections_in_order`, `empty_sections_render_with_explicit_body`, `stale_table_disclaimers_present`, `age_control_enforced`, `cross_age_window_labeled`, `trending_claims_have_minimum_age`, `confidence_labels_present`, `confidence_n_matches_comparison_set`, `confidence_thresholds_correct`, `no_em_dashes`, `no_en_dashes_as_punctuation`, `no_banned_vocab`, `no_formulaic_openers`, `first_person_plural_where_it_fits`, `no_prior_report_citation`, `multi_week_claims_self_contained`, `numbers_match_underlying_query_results`). The recipe is the source of truth; if the recipe's identifier list changes, re-derive this list rather than maintaining the two in parallel.
- `fixes_applied` is the list of inline fixes the self-audit made before publishing. Each entry has `section` (the report section where the fix landed, e.g., `"What is working"`, `"Patterns worth watching"`, or `"(audit)"` for items the audit could not verify and noted) and `fix` (a one-line description of what changed). Empty array means the draft passed cleanly with no fixes needed.

A missing `voice_audit` block on an otherwise-successful run is itself a finding: the self-audit step did not execute. Enforcement is markdown, not code, so the absence is the only after-the-fact signal that the gate was skipped. Next-run analysts should investigate any prior run whose `summary.json` lacks `voice_audit`.

## Related

- `reports/` — the human-readable archive (same content as `report.md` here, gathered in one place for browsing).
- `docs/runbook.md` — what to do when a run errors.
- `CHANGELOG.md` — when the analyzer's behavior or rules change.
