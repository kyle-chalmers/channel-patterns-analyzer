---
description: Run the weekly channel-patterns analyzer end-to-end. Pulls data-health + canonical queries from BigQuery, drafts a minimal report, publishes to Notion via the write-notion-report skill, and persists local artifacts.
disable-model-invocation: true
---

# /run-analyzer

This is the linear recipe an operator (or a cloud routine) runs to produce one weekly report. Every step has side effects (BigQuery reads, file writes, Notion writes). It is intentionally not auto-invocable.

Before drafting any prose for the report, read `CLAUDE.md` (voice, age control, sample-size thresholds, report structure) and `BUSINESS_RULES.md` (fiscal calendar, table grain, freshness contract). The recipe orchestrates; the analyzer rules live there.

## Step 0: Preflight

1. Read `.env`. Confirm `BQ_PROJECT`, `BQ_DATASET` (default `youtube_analytics` if unset), and `NOTION_REPORT_PAGE_ID` are all populated.
2. Compute the run date in Phoenix time: `run_date = $(TZ=America/Phoenix date +%Y-%m-%d)`. Phoenix is UTC-7 year-round (no DST). Use this `{run_date}` value everywhere downstream.
3. `mkdir -p runs/{run_date}/queries/ reports/`.
4. If any required env var is missing, write a minimal `runs/{run_date}/summary.json` with `errors: [{"category": "env_missing", "message": "<NAME> not set", "step": "preflight"}]`, surface the operator message naming the missing var, and STOP. No transport probe, no queries.
5. Argument handling: `/run-analyzer` takes no arguments. If `$ARGUMENTS` is non-empty, record a `warnings: ["arguments_ignored: <value>"]` entry in `summary.json` and continue. Do not interpret the argument as a flag.

## Step 1: Probe transports

Probe the session for an available BigQuery transport, in this order:

- Try `command -v bq` via Bash. If `bq` is on PATH, set `TRANSPORT=bq_cli`.
- Else check whether `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly` is loaded in the session. If yes, set `TRANSPORT=bq_mcp`.
- Else write `runs/{run_date}/summary.json` with `errors: [{"category": "no_bigquery_transport", "message": "neither bq CLI nor BigQuery MCP available", "step": "transport_probe"}]` and STOP.

Invocation shapes (use verbatim):

- `bq_cli`: `bq --format=json query --use_legacy_sql=false --max_rows=10000 --project_id="$BQ_PROJECT" "$SQL"`. The `--format=json` flag is GLOBAL and goes BEFORE the `query` subcommand. `--max_rows=10000` is mandatory (the default of 100 will silently truncate Phase 2 queries). Capture stderr separately because `bq` writes auth-refresh messages to stderr.
- `bq_mcp`: invoke `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly` with arguments `{"projectId": "<BQ_PROJECT value>", "query": "<SQL string>"}`. Note: `projectId` is camelCase and REQUIRED (the wrapper does NOT fall back to gcloud config). The response is `{"jobComplete": ..., "rows": [{"f": [{"v": ...}, ...]}, ...], "schema": {"fields": [{"name": ..., "type": ...}, ...]}, ...}`. Rows come back in positional shape: zip each row's `f` array against `schema.fields[].name` to recover column names. Numeric metadata (`totalBytesBilled`, `totalBytesProcessed`) is returned as JSON strings; coerce before any arithmetic.

## Step 2: Data health (HEALTH-01, HEALTH-02, HEALTH-03)

Read `sql/04_data_health_check.sql`. Substitute every literal `youtube_analytics` in the file contents with the value of `$BQ_DATASET` (in-memory string replace; do not edit the file on disk). The file already uses `CURRENT_DATE('America/Phoenix')` per the Phase 1 scaffold fix, so no timezone substitution is needed.

Dispatch the rewritten SQL to `$TRANSPORT`. Capture stdout to `runs/{run_date}/queries/data_health.json`. For `bq_cli`, capture stderr to `runs/{run_date}/queries/data_health.stderr` so the JSON capture stays clean. For `bq_mcp`, errors come back in the tool response itself, not stderr.

Parse the 4-row result. Each row has `table_name`, `latest_snapshot`, `days_stale`. Build:

- `snapshot_dates`: a map `{table_name: latest_snapshot}` for every row.
- `stale_tables`: a list of strings like `"daily_video_analytics (89 days)"` for every row whose `days_stale > 3`.

Failure routing:

- If `bq_cli` stderr contains `Reauthentication failed`, `cannot prompt during non-interactive`, or `Could not load the default credentials` (or for `bq_mcp`, the response has an auth-style error), record `errors: [{"category": "bq_auth", "message": "<first line>", "step": "data_health"}]`. Operator message names docs/runbook.md section "BigQuery auth failure". STOP after writing summary.json in Step 7.
- If the response contains `Not found: Table`, record `errors: [{"category": "missing_table", "message": "<error>", "step": "data_health"}]`. Operator message names docs/runbook.md section "Required table is missing or empty". STOP.
- If parsed result has zero rows, record `errors: [{"category": "empty_result", "message": "0 rows from sql/04", "step": "data_health"}]`. Operator message names docs/runbook.md section "Required table is missing or empty". STOP.

## Step 3: Top-videos pull (BQ-01, BQ-02)

Read `sql/02_top_full_length_videos.sql`. Substitute `youtube_analytics` -> `$BQ_DATASET` the same way. This query joins `video_metadata` and `daily_video_stats` on `(video_id, snapshot_date)` per BUSINESS_RULES.md §4 (never on `video_id` alone, which would Cartesian-explode across snapshots).

Dispatch to `$TRANSPORT`. Capture stdout to `runs/{run_date}/queries/top_full_length_videos.json` (and stderr to the matching `.stderr` file for `bq_cli`).

If `daily_video_stats` appeared in `stale_tables` from Step 2, record the staleness flag for Step 4 so the "What is working" section can disclaim it (HEALTH-03). If `daily_video_analytics` is stale, that affects the empty-by-design Phase 1 sections (which already say "not analyzed this run"); note it but do not block.

If the query returns zero rows, this is a BQ-03 failure: record `errors: [{"category": "empty_result", "message": "0 rows from sql/02", "step": "top_videos"}]`, queue the operator message naming docs/runbook.md section "Required table is missing or empty", and proceed to Step 4 with an empty `working[]` list. The report still ships with a labeled placeholder; the failure is captured in summary.json.

## Step 4: Draft the report (PERSIST-01)

Compose the markdown report per CLAUDE.md §"Report structure" and the Phase 1 default from `.planning/phases/01-first-notion-report-end-to-end/01-CONTEXT.md` (Data Health + Headline + one What's-working finding sourced from sql/02, with labeled placeholders for What's not working, Patterns worth watching, Open questions). All six section headings appear, every time. Never silently omit a section.

Voice rules from CLAUDE.md apply: no em dashes, no banned vocabulary ("leverage", "robust", "seamless", "delve", "transformative"), no formulaic openers ("Great news!", "In conclusion,"), first-person plural where it fits, vary sentence length.

For the Data Health section: render a table of the 4 rows from Step 2, then a one-sentence prose summary. If `stale_tables` is non-empty, the prose names each stale table and notes which downstream sections are constrained. If empty, the prose says all four tables are within the 3-day freshness contract.

For the What's working finding: pick the top row from Step 3 (highest view count), include title, view_count, days_since_published, and label confidence "low" (per RESEARCH §10 Q6: this is a raw top-N reading, not a pattern claim). If `daily_video_stats` is stale, disclaim the staleness in this section.

Write the assembled markdown to `reports/{run_date}.md`. Also copy the same content to `runs/{run_date}/report.md` per the folder layout in `runs/README.md`.

<!-- Steps 5-7 added in Task 2 -->
