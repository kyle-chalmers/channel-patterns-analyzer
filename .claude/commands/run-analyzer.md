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

## Step 5: Assemble the report dict

Build a strict 8-key dict matching the `write-notion-report` Skill's input contract (defined in `.claude/skills/write-notion-report/SKILL.md`):

- `run_date`: string `YYYY-MM-DD` (from Step 0).
- `data_health`: `{"snapshot_dates": {table: date}, "stale_tables": [string, ...]}` (both built in Step 2).
- `headline`: 1-2 sentence string from the headline drafted in Step 4.
- `working`: list of `{title, body, confidence}` dicts. In Phase 1 this has exactly one entry (the top-videos finding from Step 3), with `confidence: "low"` per CONTEXT.md (this is a raw top-N reading, not a pattern claim).
- `not_working`: `[]` (Phase 2 wires this).
- `patterns`: `[]` (Phase 2 wires this).
- `open_questions`: `[]` (Phase 2 wires this).
- `markdown_body`: the full report markdown from Step 4.

Validate before Step 6: if any key is missing, do NOT invoke the Skill. Record `errors: [{"category": "report_dict_invalid", "message": "missing key: <name>", "step": "assemble_dict"}]` and proceed to Step 7 to write summary.json.

## Step 6: Invoke write-notion-report (NOTION-01..06)

Invoke the `write-notion-report` Skill with the assembled dict. The Skill returns one of:

- `{"ok": true, "page_id": "<uuid>", "url": "<notion url>"}` on success.
- `{"ok": false, "error": "<string>", "category": "<env_missing|parent_not_found|permission_denied|transport_error|unknown>"}` on failure.

Capture the return value. CRITICAL: do NOT fail the run if the Skill returns `ok: false`. Local artifacts already exist from Steps 2-4; Step 7 captures the Skill's failure in summary.json. The report has landed in `reports/{run_date}.md` regardless.

If the Skill is not loaded in the session (the `.claude/skills/write-notion-report/SKILL.md` file is missing or the runtime did not pick it up), treat as `{"ok": false, "category": "skill_unavailable"}`, queue the operator message naming docs/runbook.md section "Notion write failed", and proceed to Step 7.

## Step 7: Write summary.json (PERSIST-02, ERR-02)

Write `runs/{run_date}/summary.json` LAST, per the schema in `runs/README.md` (which includes the additive `transport` and `notion_url` fields the Phase 1 scaffold added). Full field set:

- `run_date`: from Step 0.
- `run_started_at`, `run_finished_at`: ISO-8601 with Phoenix offset `-07:00`.
- `data_source`: `"bigquery"` (Phase 1 is BQ-only; CSV-01 lands in Phase 3).
- `transport`: `"bq_cli"` or `"bq_mcp"` from Step 1.
- `bq_project`, `bq_dataset`: from `.env`.
- `snapshot_dates`: from Step 2.
- `stale_tables`: from Step 2.
- `video_count_full_length`: row count from Step 3.
- `queries_run`: list with `{"file": ..., "rows": ..., "ms": ...}` per query that actually executed.
- `report_path`: `"reports/{run_date}.md"`.
- `notion_write_ok`: boolean from Step 6.
- `notion_page_id`, `notion_url`: from Step 6 success path; omit or set null on failure.
- `errors`: list (may be empty); each entry `{"category": ..., "message": ..., "step": ...}`.

PERSIST-03 contract: the write order is queries -> report -> Skill -> summary.json LAST. If any step in 2-6 throws, Step 7 still runs. Implementation: after each step that succeeds, append the cumulative state to `runs/{run_date}/.partial-state.json` (transient file, dot-prefixed). If any step throws, Step 7 reads `.partial-state.json`, merges in the captured error, writes the final `summary.json`, and deletes the partial file. The partial file lives only between throw and Step 7; it is never committed.

Always write summary.json. Never skip it. This is the ERR-02 contract.

## Step 8: Operator message

Print exactly one of three patterns, then exit:

- SUCCESS: `Run {run_date} complete. Notion: {url}. Local: reports/{run_date}.md`
- NOTION-FAIL: `Run {run_date} complete locally but Notion write failed: {category}. Recovery: see docs/runbook.md § 'Notion write failed'. Local: reports/{run_date}.md`
- BQ-FAIL: `Run {run_date} FAILED at {step}: {error}. Recovery: see docs/runbook.md § '{relevant section}'.`

The three patterns are exhaustive: every run finishes with one of them. For BQ-FAIL, the relevant docs/runbook.md section is one of "BigQuery auth failure", "Required table is missing or empty", or "A required table is stale", chosen by the error category recorded in Step 2 or Step 3.
