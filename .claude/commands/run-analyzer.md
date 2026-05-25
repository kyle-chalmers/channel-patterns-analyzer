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

- `bq_cli`: `printf '%s' "$SQL" | bq --format=json query --use_legacy_sql=false --project_id="$BQ_PROJECT"`. SQL goes in via **stdin pipe**, never as a positional argument. The `--format=json` flag is GLOBAL and goes BEFORE the `query` subcommand. Capture stderr separately because `bq` writes auth-refresh messages to stderr. Row-count control is handled at the SQL level (use `LIMIT` inside the SQL file if a cap is needed); do NOT pass `--max_rows` to `bq query`. That flag is not valid for the `query` subcommand and crashes bq's argument parser with a Python `RecursionError`. The Phase 1 default 100-row cap is the only fallback; Plan 02-01 removed `LIMIT 20` from `sql/02` and `sql/03`, so very large result sets in those queries would be capped at 100 rows by bq's default. The dataset is small enough (~23 full-length videos) that this is not a practical concern; if it ever becomes one, raise the cap via `--n` (which the `query` subcommand does accept) or push a `LIMIT` into the SQL.
- The stdin-pipe form is also required because every `sql/` file in this repo uses Unicode box-drawing characters (`─` U+2500) in its header comment. Passing those characters as a positional argument trips the same `RecursionError` in bq's flag-suggester (the parser treats the leading dash as flag-like). Piping via stdin avoids that path entirely. The `bq_mcp` branch is unaffected (SQL crosses the wire as a JSON string argument).
- `bq_mcp`: invoke `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly` with arguments `{"projectId": "<BQ_PROJECT value>", "query": "<SQL string>"}`. Note: `projectId` is camelCase and REQUIRED (the wrapper does NOT fall back to gcloud config). The response is `{"jobComplete": ..., "rows": [{"f": [{"v": ...}, ...]}, ...], "schema": {"fields": [{"name": ..., "type": ...}, ...]}, ...}`. Rows come back in positional shape: zip each row's `f` array against `schema.fields[].name` to recover column names. Numeric metadata (`totalBytesBilled`, `totalBytesProcessed`) is returned as JSON strings; coerce before any arithmetic.

**Transport smoke-test note (first-time operators):** Run the recipe once with `BQ_TRANSPORT=bq_cli` and once with `BQ_TRANSPORT=bq_mcp` to confirm both paths produce identical row counts for `data_health` and `top_full_length_videos`. Phase 1 only exercised `bq_cli` live; the MCP branch is documented but unverified end-to-end. A divergence between the two transports on the same snapshot is a transport bug, not a data bug.

## Step 2: Data health (HEALTH-01, HEALTH-02, HEALTH-03)

Read `sql/04_data_health_check.sql`. Substitute every literal `youtube_analytics` in the file contents with the value of `$BQ_DATASET` (in-memory string replace; do not edit the file on disk). The file already uses `CURRENT_DATE('America/Phoenix')` per the Phase 1 scaffold fix, so no timezone substitution is needed.

Dispatch the rewritten SQL to `$TRANSPORT`. Capture stdout to `runs/{run_date}/queries/data_health.json`. For `bq_cli`, capture stderr to `runs/{run_date}/queries/data_health.stderr` so the JSON capture stays clean. For `bq_mcp`, errors come back in the tool response itself, not stderr.

Parse the 4-row result. Each row has `table_name`, `latest_snapshot`, `days_stale`. Build:

- `snapshot_dates`: a map `{table_name: latest_snapshot}` for every row.
- `stale_tables`: a list of strings like `"daily_video_analytics (89 days)"` for every row whose `days_stale > 3`.

**`SIMULATE_STALE` override (testing only):** If the env var `SIMULATE_STALE` is set, parse it as a comma-separated list of `table_name:days` pairs and override the parsed `days_stale` for the named tables before computing `stale_tables`. Example: `SIMULATE_STALE="daily_video_analytics:89,daily_traffic_sources:89"` simulates the 89-day-stale state the channel had on 2026-05-24. The override mutates the in-memory `data_health` rows only; it does NOT modify the BigQuery result on disk (`runs/{run_date}/queries/data_health.json` still contains the real values). Record a `warnings: ["simulate_stale_applied: <value of SIMULATE_STALE>"]` entry in `summary.json` when the override fires, so the audit trail shows the data was synthetic. This exists because Phase 1's 89-day stale state on `daily_video_analytics` and `daily_traffic_sources` resolved on 2026-05-25, leaving no live way to exercise the stale-table disclaimer machinery (D-12) end-to-end. The override is a recipe-level seam; it does not require a CLI flag, an SQL edit, or a BigQuery change.

Failure routing:

- If `bq_cli` stderr contains `Reauthentication failed`, `cannot prompt during non-interactive`, or `Could not load the default credentials` (or for `bq_mcp`, the response has an auth-style error), record `errors: [{"category": "bq_auth", "message": "<first line>", "step": "data_health"}]`. Operator message names docs/runbook.md section "BigQuery auth failure". STOP after writing summary.json in Step 9.
- If the response contains `Not found: Table`, record `errors: [{"category": "missing_table", "message": "<error>", "step": "data_health"}]`. Operator message names docs/runbook.md section "Required table is missing or empty". STOP.
- If parsed result has zero rows, record `errors: [{"category": "empty_result", "message": "0 rows from sql/04", "step": "data_health"}]`. Operator message names docs/runbook.md section "Required table is missing or empty". STOP.

## Step 3: Top-videos pull (BQ-01, BQ-02)

Read `sql/02_top_full_length_videos.sql`. Substitute `youtube_analytics` -> `$BQ_DATASET` the same way. This query joins `video_metadata` and `daily_video_stats` on `(video_id, snapshot_date)` per `BUSINESS_RULES.md § "Table grain and join keys (data contract)"` (never on `video_id` alone, which would Cartesian-explode across snapshots).

Dispatch to `$TRANSPORT`. Capture stdout to `runs/{run_date}/queries/top_full_length_videos.json` (and stderr to the matching `.stderr` file for `bq_cli`).

If `daily_video_stats` appeared in `stale_tables` from Step 2, record the staleness flag for Step 6 so the "What is working" section can disclaim it (HEALTH-03). If `daily_video_analytics` is stale, that affects the empty-by-design Phase 1 sections (which already say "not analyzed this run"); note it but do not block.

If the query returns zero rows, this is a BQ-03 failure: record `errors: [{"category": "empty_result", "message": "0 rows from sql/02", "step": "top_videos"}]`, queue the operator message naming docs/runbook.md section "Required table is missing or empty", and proceed to Step 6 with an empty `working[]` list. The report still ships with a labeled placeholder; the failure is captured in summary.json.

## Step 4: Read prior reports for calibration

This step implements ANALYSIS-05 and D-08 from `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`. Run AFTER Step 3 (top-videos pull) and BEFORE the draft step.

1. List existing reports excluding today's date (today's same-day retry, if any, belongs to "this run", not the calibration archive):
   ```bash
   ls reports/ | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}(-[0-9]+)?\.md$' | grep -v "^${run_date}" | sort | tail -n 3
   ```
   The naming convention is `YYYY-MM-DD.md` (steady state) or `YYYY-MM-DD-N.md` (same-day retry); ISO-8601 lexicographic sort yields chronological order, and same-day retries sort after the original.
2. Read those files in full (zero, one, two, or three of them, whatever exists). Hold the content in working memory for the draft step.
3. For each file read, also read its sibling `runs/{date}/summary.json` and capture the `snapshot_dates` map. This is the per-run snapshot calibration logic: confidence calibration uses the *observed* snapshot_dates from each prior run, not assumptions about state continuity. Critical context: the 89-day stale state on `daily_video_analytics` and `daily_traffic_sources` resolved between 2026-05-24 and 2026-05-25, so reading the prior `summary.json` is the only way to know which sections of each prior report were drawing from fresh vs. stale data at the time.
4. Use prior reports to:
   - **Upgrade confidence labels** if a pattern has held across runs and the eligible set has grown (e.g., what was `moderate confidence, n=7` four weeks ago may now be `standard confidence, n=12`).
   - **Downgrade confidence** if a pattern has weakened or the sample shrank.
   - **Avoid restating findings verbatim.** Fresh-frame the same patterns; do not copy sentences.
   - **Notice regressions.** Was a video a top performer two reports ago and isn't now?
5. Do NOT cite the prior reports in the new report's prose (D-08). The standalone-tone rule in CLAUDE.md ("assume Kyle has not seen the previous week's report") holds. Cross-week framing is allowed per D-09 only when self-contained.
   - Allowed example: `"For the third consecutive week, tool-specific tutorials are pulling 4×+ the views of conceptual videos."`
   - Banned phrases: `"as we said last week"`, `"as noted previously"`, `"the prior report"`, `"this continues the trend we observed"`, `"as noted"`.
6. Record the dates actually consulted as a JSON array of `YYYY-MM-DD` strings (e.g., `["2026-05-18", "2026-05-11", "2026-05-04"]`). Hold this list in working memory until Step 9 (write summary.json) writes it to `summary.json.prior_reports_consulted` (D-10). If zero prior reports were consulted (the archive is empty), the recorded value is `[]`. Verify at draft time that the list does not include today's `run_date`. Same-day retries belong to "this run", not the calibration archive.

Zero-or-few-priors handling: if fewer than three reports exist (or none), read what is there and continue. Do not block. The first Phase 2 run will have at most one prior report (the Phase 1 report from 2026-05-25).

## Step 5: Query live eligible video count

This step implements ANALYSIS-03 and D-07. The `N` in `(label, n=N)` parentheticals comes from a live count each run, never hardcoded (CLAUDE.md § "Small samples get hedged, every time" rule). Run AFTER the prior-report read step and BEFORE the draft step.

Compose the eligible-count SQL inline (no new `sql/` file; the recipe owns this query):

```sql
WITH latest_common AS (
    SELECT LEAST(
        (SELECT MAX(snapshot_date) FROM `${BQ_DATASET}.video_metadata`),
        (SELECT MAX(snapshot_date) FROM `${BQ_DATASET}.daily_video_stats`)
    ) AS snapshot_date
)
SELECT
    COUNT(*) AS eligible_count,
    (SELECT COUNT(*) FROM `${BQ_DATASET}.video_metadata` m2
        WHERE m2.snapshot_date = (SELECT snapshot_date FROM latest_common)
          AND m2.video_type = 'full_length') AS total_full_length,
    (SELECT snapshot_date FROM latest_common) AS latest_common_snapshot
FROM `${BQ_DATASET}.video_metadata` m
WHERE m.snapshot_date = (SELECT snapshot_date FROM latest_common)
    AND m.video_type = 'full_length'
    AND DATE_DIFF(CURRENT_DATE("America/Phoenix"), DATE(m.published_at), DAY) >= 14;
```

Substitute `${BQ_DATASET}` with `$BQ_DATASET` (in-memory; do not write the rewritten SQL to disk). Dispatch via `$TRANSPORT` using the Step 1 invocation shape (`printf '%s' "$SQL" | bq --format=json query ...` for `bq_cli`; `execute_sql_readonly` for `bq_mcp`).

Persist the raw query result to `runs/{run_date}/queries/eligible_video_count.json` (BQ-02 convention) so the audit trail captures the denominator behind every confidence label this run.

Derive the channel-wide confidence label from `eligible_count` per CLAUDE.md § "Small samples get hedged, every time":

| `eligible_count` | label |
|---|---|
| `< 5` (i.e., n=4 or fewer) | `low confidence` |
| `5 to 10` (i.e., n=5, 6, 7, 8, 9, 10) | `moderate confidence` |
| `>= 10` (i.e., n=10 or more; the table reads `10 or more` per CLAUDE.md) | `standard confidence` |

Boundary clarification (verified A6 in `02-RESEARCH.md`): `n=4` → low, `n=5` → moderate, `n=10` → standard. CLAUDE.md's "5 to 10" range is inclusive of 5; "10 or more" is inclusive of 10. The standard-tier boundary wins at exactly 10.

Cache the channel-wide eligible count for the duration of the run; the draft step uses it for any claim drawn from the full eligible set. Sub-population claims (e.g., "only tutorials") MUST scope their own counts and cite the sub-population `n`, not the channel-wide eligible count (per RESEARCH.md Pitfall 2, a tutorial-only claim cites `n=7`, not the channel-wide `n=18`).

Output (held in working memory for the draft step): `{eligible_count: N, total_full_length: M, latest_common_snapshot: "YYYY-MM-DD"}`.

## Step 6: Draft the report (PERSIST-01)

Compose the markdown report per CLAUDE.md §"Report structure" and the Phase 1 default from `.planning/phases/01-first-notion-report-end-to-end/01-CONTEXT.md` (Data Health + Headline + one What's-working finding sourced from sql/02, with labeled placeholders for What's not working, Patterns worth watching, Open questions). All six section headings appear, every time. Never silently omit a section.

Voice rules from CLAUDE.md apply: no em dashes, no banned vocabulary ("leverage", "robust", "seamless", "delve", "transformative"), no formulaic openers ("Great news!", "In conclusion,"), first-person plural where it fits, vary sentence length.

For the Data Health section: render a table of the 4 rows from Step 2, then a one-sentence prose summary. If `stale_tables` is non-empty, the prose names each stale table and notes which downstream sections are constrained. If empty, the prose says all four tables are within the 3-day freshness contract.

For the What's working finding: pick the top row from Step 3 (highest view count), include title, view_count, days_since_published, and label confidence "low" (per RESEARCH §10 Q6: this is a raw top-N reading, not a pattern claim). If `daily_video_stats` is stale, disclaim the staleness in this section.

Write the assembled markdown to `reports/{run_date}.md`. Also copy the same content to `runs/{run_date}/report.md` per the folder layout in `runs/README.md`.

## Step 7: Assemble the report dict

Build a strict 8-key dict matching the `write-notion-report` Skill's input contract (defined in `.claude/skills/write-notion-report/SKILL.md`):

- `run_date`: string `YYYY-MM-DD` (from Step 0).
- `data_health`: `{"snapshot_dates": {table: date}, "stale_tables": [string, ...]}` (both built in Step 2).
- `headline`: 1-2 sentence string from the headline drafted in Step 6.
- `working`: list of `{title, body, confidence}` dicts. In Phase 1 this has exactly one entry (the top-videos finding from Step 3), with `confidence: "low"` per CONTEXT.md (this is a raw top-N reading, not a pattern claim).
- `not_working`: `[]` (Phase 2 wires this).
- `patterns`: `[]` (Phase 2 wires this).
- `open_questions`: `[]` (Phase 2 wires this).
- `markdown_body`: the full report markdown from Step 6.

Validate before Step 8: if any key is missing, do NOT invoke the Skill. Record `errors: [{"category": "report_dict_invalid", "message": "missing key: <name>", "step": "assemble_dict"}]` and proceed to Step 9 to write summary.json.

## Step 8: Invoke write-notion-report (NOTION-01..06)

Invoke the `write-notion-report` Skill with the assembled dict. The Skill returns one of:

- `{"ok": true, "page_id": "<uuid>", "url": "<notion url>"}` on success.
- `{"ok": false, "error": "<string>", "category": "<env_missing|parent_not_found|permission_denied|transport_error|unknown>"}` on failure.

Capture the return value. CRITICAL: do NOT fail the run if the Skill returns `ok: false`. Local artifacts already exist from the data-health, top-videos, eligible-count, prior-report, and draft steps; the write-summary step captures the Skill's failure in summary.json. The report has landed in `reports/{run_date}.md` regardless.

If the Skill is not loaded in the session (the `.claude/skills/write-notion-report/SKILL.md` file is missing or the runtime did not pick it up), treat as `{"ok": false, "category": "skill_unavailable"}`, queue the operator message naming docs/runbook.md section "Notion write failed", and proceed to the write-summary step.

## Step 9: Write summary.json (PERSIST-02, ERR-02)

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
- `notion_write_ok`: boolean from Step 8.
- `notion_page_id`, `notion_url`: from the Skill-invoke step's success path; omit or set null on failure.
- `prior_reports_consulted`: JSON array of `YYYY-MM-DD` strings recording which prior `reports/{date}.md` files were read during the prior-report calibration step (D-10). MAY be empty (`[]`) if fewer than three prior reports exist or none were consulted.
- `errors`: list (may be empty); each entry `{"category": ..., "message": ..., "step": ...}`.
- `warnings`: list (may be empty); each entry is a human-readable string. Used for non-fatal events that an auditor should see (e.g., `simulate_stale_applied: ...`, `arguments_ignored: ...`).

PERSIST-03 contract: the write order is queries -> report -> Skill -> summary.json LAST. If any earlier step throws, this step still runs. Implementation: after each step that succeeds, append the cumulative state to `runs/{run_date}/.partial-state.json` (transient file, dot-prefixed). If any step throws, this step reads `.partial-state.json`, merges in the captured error, writes the final `summary.json`, and deletes the partial file. The partial file lives only between throw and the write-summary step; it is never committed.

Always write summary.json. Never skip it. This is the ERR-02 contract.

## Step 10: Operator message

Print exactly one of three patterns, then exit:

- SUCCESS: `Run {run_date} complete. Notion: {url}. Local: reports/{run_date}.md`
- NOTION-FAIL: `Run {run_date} complete locally but Notion write failed: {category}. Recovery: see docs/runbook.md § 'Notion write failed'. Local: reports/{run_date}.md`
- BQ-FAIL: `Run {run_date} FAILED at {step}: {error}. Recovery: see docs/runbook.md § '{relevant section}'.`

The three patterns are exhaustive: every run finishes with one of them. For BQ-FAIL, the relevant docs/runbook.md section is one of "BigQuery auth failure", "Required table is missing or empty", or "A required table is stale", chosen by the error category recorded in Step 2 or Step 3.
