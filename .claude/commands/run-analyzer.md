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
5. **Validate `BQ_DATASET` against BigQuery identifier rules.** `BQ_DATASET` is string-substituted into backtick-quoted SQL identifiers in Steps 2, 3, and 5 (e.g., `` `${BQ_DATASET}.video_metadata` ``). A value containing a backtick, a comma, or other BigQuery metacharacters could break out of the backtick quoting and either parse-error noisily or query an unintended dataset. Treat `BQ_DATASET` as a potentially-hostile input even though `.env` is operator-controlled (defense in depth).
   - Required regex: `^[A-Za-z_][A-Za-z0-9_]*$` (BigQuery dataset identifier rules: letter or underscore start, then letters/digits/underscores).
   - If `BQ_DATASET` fails this check, write `runs/{run_date}/summary.json` with `errors: [{"category": "env_invalid", "message": "BQ_DATASET contains non-identifier characters: <value>", "step": "preflight"}]`, surface the operator message naming the invalid env var, and STOP. No transport probe, no queries.
   - `BQ_PROJECT` is passed to `bq` via `--project_id="$BQ_PROJECT"` (positional, never string-substituted into SQL) and to the MCP wrapper as a JSON argument, so it does not need the same treatment. Still reject obviously malformed values (empty after trim, contains whitespace) as a sanity check.
6. Argument handling: `/run-analyzer` takes no arguments. If `$ARGUMENTS` is non-empty, record a `warnings: ["arguments_ignored: <value>"]` entry in `summary.json` and continue. Do not interpret the argument as a flag.

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

Read `sql/04_data_health_check.sql`. Substitute every literal `youtube_analytics` in the file contents with the value of `$BQ_DATASET` (in-memory string replace; do not edit the file on disk). The file already uses `CURRENT_DATE("America/Phoenix")` (double-quoted, the canonical form Plan 02-01 standardized on across `sql/02..04`), so no timezone substitution is needed.

Dispatch the rewritten SQL to `$TRANSPORT`. Capture stdout to `runs/{run_date}/queries/data_health.json`. For `bq_cli`, capture stderr to `runs/{run_date}/queries/data_health.stderr` so the JSON capture stays clean. For `bq_mcp`, errors come back in the tool response itself, not stderr.

Parse the 4-row result. Each row has `table_name`, `latest_snapshot`, `days_stale`. Build:

- `snapshot_dates`: a map `{table_name: latest_snapshot}` for every row.
- `stale_tables`: a list of strings like `"daily_video_analytics (89 days)"` for every row whose `days_stale > 3`.

**`SIMULATE_STALE` override (testing only):** If the env var `SIMULATE_STALE` is set, parse it as a comma-separated list of `table_name:days` pairs and override the parsed `days_stale` for the named tables before computing `stale_tables`. Example: `SIMULATE_STALE="daily_video_analytics:89,daily_traffic_sources:89"` simulates the 89-day-stale state the channel had on 2026-05-24. The override mutates the in-memory `data_health` rows only; it does NOT modify the BigQuery result on disk (`runs/{run_date}/queries/data_health.json` still contains the real values). Record a `warnings: ["simulate_stale_applied: <value of SIMULATE_STALE>"]` entry in `summary.json` when the override fires, so the audit trail shows the data was synthetic. This exists because Phase 1's 89-day stale state on `daily_video_analytics` and `daily_traffic_sources` resolved on 2026-05-25, leaving no live way to exercise the stale-table disclaimer machinery (D-12) end-to-end. The override is a recipe-level seam; it does not require a CLI flag, an SQL edit, or a BigQuery change.

**SIMULATE_STALE validation (required before applying any override):**

1. Each comma-separated pair MUST match the regex `^(video_metadata|daily_video_stats|daily_video_analytics|daily_traffic_sources):\d+$`. Table-name typos (`daily_video_analytic:89`), garbage values (`../../etc/passwd:foo`), and non-integer days (`video_metadata:soon`) all fail this check.
2. If ANY pair fails validation, do NOT partial-apply. Record `warnings: ["simulate_stale_invalid: <raw value of SIMULATE_STALE>"]` in `summary.json` and skip the override entirely. All four `data_health` rows keep their real `days_stale` values.
3. If every pair passes validation but a `table_name` is not present in the parsed `data_health` rows (e.g., `sql/04` returned three rows instead of four), record `warnings: ["simulate_stale_table_not_in_health_rows: <table_name>"]` and continue applying the overrides that do match. A SQL/parser mismatch is worth surfacing without aborting the whole override.

The silent-failure mode the validation prevents: an operator typos a table name to test the D-12 disclaimer rule, sees no stale flag in the report, and concludes the test passed when in fact the override never fired.

Failure routing:

- If `bq_cli` stderr contains `Reauthentication failed`, `cannot prompt during non-interactive`, or `Could not load the default credentials` (or for `bq_mcp`, the response has an auth-style error), record `errors: [{"category": "bq_auth", "message": "<first line>", "step": "data_health"}]`. Operator message names docs/runbook.md section "BigQuery auth failure". STOP after writing summary.json in Step 10.
- If the response contains `Not found: Table`, record `errors: [{"category": "missing_table", "message": "<error>", "step": "data_health"}]`. Operator message names docs/runbook.md section "Required table is missing or empty". STOP.
- If parsed result has zero rows, record `errors: [{"category": "empty_result", "message": "0 rows from sql/04", "step": "data_health"}]`. Operator message names docs/runbook.md section "Required table is missing or empty". STOP.
- If any row has `latest_snapshot IS NULL` (the underlying source table is genuinely empty; `MAX(snapshot_date) FROM <empty_table>` returns one row with NULL, not zero rows, so the zero-rows check above does not fire on this case), record `errors: [{"category": "empty_result", "message": "<table_name> has no rows (latest_snapshot is NULL)", "step": "data_health"}]`. Operator message names docs/runbook.md section "Required table is missing or empty". STOP. Without this check, an empty `video_metadata` or `daily_video_stats` would let Step 5's `LEAST(NULL, X)` resolve to NULL, the recipe would proceed to compute `eligible_count = 0`, and every channel-wide claim would silently land at `low confidence, n=0` instead of stopping. This is the SQL-layer NULL guard's necessary Step-2-side companion.

## Step 3: Top-videos pull (BQ-01, BQ-02)

Read `sql/02_top_full_length_videos.sql`. Substitute `youtube_analytics` -> `$BQ_DATASET` the same way. This query joins `video_metadata` and `daily_video_stats` on `(video_id, snapshot_date)` per `BUSINESS_RULES.md § "Table grain and join keys (data contract)"` (never on `video_id` alone, which would Cartesian-explode across snapshots).

Dispatch to `$TRANSPORT`. Capture stdout to `runs/{run_date}/queries/top_full_length_videos.json` (and stderr to the matching `.stderr` file for `bq_cli`).

If `daily_video_stats` appeared in `stale_tables` from Step 2, record the staleness flag for Step 6 so the "What is working" section can disclaim it (HEALTH-03). If `daily_video_analytics` is stale, that affects the empty-by-design Phase 1 sections (which already say "not analyzed this run"); note it but do not block.

If the query returns zero rows, this is a BQ-03 failure: record `errors: [{"category": "empty_result", "message": "0 rows from sql/02", "step": "top_videos"}]`, queue the operator message naming docs/runbook.md section "Required table is missing or empty", and proceed to Step 6 with an empty `working[]` list. The report still ships with a labeled placeholder; the failure is captured in summary.json.

## Step 4: Read prior reports for calibration

This step implements ANALYSIS-05 and D-08 from `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`. Run AFTER Step 3 (top-videos pull) and BEFORE the draft step.

1. Select the **3 most recent distinct prior dates** from `reports/`, excluding today's date (today's same-day retry, if any, belongs to "this run", not the calibration archive). Lexicographic `sort | tail -n 3` over filenames is wrong here: same-day retries (`YYYY-MM-DD-N.md`) sort after the original and would let a single prior date monopolize all three slots. Pick distinct dates first, then resolve each date to its canonical file:
   ```bash
   # 1a. Extract distinct prior dates (newest 3, excluding today):
   prior_dates=$(ls reports/ \
     | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}(-[0-9]+)?\.md$' \
     | sed -E 's/^([0-9]{4}-[0-9]{2}-[0-9]{2}).*/\1/' \
     | sort -u \
     | grep -v "^${run_date}$" \
     | tail -n 3)

   # 1b. For each selected date, the canonical report is either
   #     `{date}.md` (steady state) or the highest-suffix `{date}-N.md`
   #     (latest same-day retry wins as the canonical record for that date).
   for d in $prior_dates; do
     latest=$(ls reports/ | grep -E "^${d}(-[0-9]+)?\.md$" | sort -V | tail -n 1)
     # read reports/$latest
   done
   ```
   The naming convention is `YYYY-MM-DD.md` (steady state) or `YYYY-MM-DD-N.md` (same-day retry). The two-step selection (distinct dates first, then highest-suffix within each date) guarantees three different prior dates are read whenever three or more exist in the archive, which is what the calibration logic requires.

   **Assertion:** The list of dates assembled in step 6 below (`prior_reports_consulted`) MUST contain only distinct `YYYY-MM-DD` values. If two same-date entries ever appear, the selection above failed and the run should record `warnings: ["prior_report_selection_duplicate_date: <date>"]` in `summary.json`.
2. Read those files in full (zero, one, two, or three of them, whatever exists). Hold the content in working memory for the draft step.
3. For each file read, also read its sibling `runs/{date}/summary.json` and capture the `snapshot_dates` map. This is the per-run snapshot calibration logic: confidence calibration uses the *observed* snapshot_dates from each prior run, not assumptions about state continuity. Critical context: the 89-day stale state on `daily_video_analytics` and `daily_traffic_sources` resolved between 2026-05-24 and 2026-05-25, so reading the prior `summary.json` is the only way to know which sections of each prior report were drawing from fresh vs. stale data at the time.
4. Use prior reports to:
   - **Upgrade confidence labels** if a pattern has held across runs and the eligible set has grown (e.g., what was `moderate confidence, n=7` four weeks ago may now be `standard confidence, n=12`).
   - **Downgrade confidence** if a pattern has weakened or the sample shrank.
   - **Avoid restating findings verbatim.** Fresh-frame the same patterns; do not copy sentences.
   - **Notice regressions.** Was a video a top performer two reports ago and isn't now?
5. Do NOT cite the prior reports in the new report's prose (D-08). The standalone-tone rule in CLAUDE.md ("assume Kyle has not seen the previous week's report") holds. Cross-week framing is allowed per D-09 only when self-contained.
   - Allowed example: `"For the third consecutive week, tool-specific tutorials are pulling 4×+ the views of conceptual videos."`
   - Banned phrases: `"as we said last week"`, `"as noted previously"`, `"the prior report"`, `"this continues the trend we observed"`. (The bare phrase `"as noted"` is intentionally NOT in this list because it false-positives on legitimate prose like `"as noted in the data"` or `"as noted above"`. The fuller `"as noted previously"` already catches the prior-report-citation case.)
6. Record the dates actually consulted as a JSON array of `YYYY-MM-DD` strings (e.g., `["2026-05-18", "2026-05-11", "2026-05-04"]`). Hold this list in working memory until Step 10 (write summary.json) writes it to `summary.json.prior_reports_consulted` (D-10). If zero prior reports were consulted (the archive is empty), the recorded value is `[]`. Verify at draft time that the list does not include today's `run_date`. Same-day retries belong to "this run", not the calibration archive.

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
        WHERE (SELECT snapshot_date FROM latest_common) IS NOT NULL
          AND m2.snapshot_date = (SELECT snapshot_date FROM latest_common)
          AND m2.video_type = 'full_length') AS total_full_length,
    (SELECT snapshot_date FROM latest_common) AS latest_common_snapshot
FROM `${BQ_DATASET}.video_metadata` m
WHERE (SELECT snapshot_date FROM latest_common) IS NOT NULL
    AND m.snapshot_date = (SELECT snapshot_date FROM latest_common)
    AND m.video_type = 'full_length'
    AND DATE_DIFF(CURRENT_DATE("America/Phoenix"), DATE(m.published_at), DAY) >= 14;
```

**NULL-guard note:** the `(SELECT snapshot_date FROM latest_common) IS NOT NULL` clauses above are deliberate. If either `video_metadata` or `daily_video_stats` is empty, `LEAST(NULL, X)` returns NULL, which would silently produce `eligible_count = 0` and a 0 denominator for confidence labels (CR-02). The Step 2 data-health check is the primary STOP for empty source tables; these guards are defense-in-depth at the SQL layer.

Substitute `${BQ_DATASET}` with `$BQ_DATASET` (in-memory; do not write the rewritten SQL to disk). Dispatch via `$TRANSPORT` using the Step 1 invocation shape (`printf '%s' "$SQL" | bq --format=json query ...` for `bq_cli`; `execute_sql_readonly` for `bq_mcp`).

Persist the raw query result to `runs/{run_date}/queries/eligible_video_count.json` (BQ-02 convention) so the audit trail captures the denominator behind every confidence label this run.

Derive the channel-wide confidence label from `eligible_count` per CLAUDE.md § "Small samples get hedged, every time":

| `eligible_count` | label |
|---|---|
| `< 5` (n=1, 2, 3, 4) | `low confidence` |
| `5 <= n < 10` (n=5, 6, 7, 8, 9) | `moderate confidence` |
| `>= 10` (n=10 or more) | `standard confidence` |

The table ranges are non-overlapping. `n=10` falls into the standard-tier row only. This resolves the documented ambiguity in CLAUDE.md § "Small samples get hedged" where "5 to 10" and "10 or more" both name n=10; the standard-tier boundary wins, verified as A6 in `02-RESEARCH.md`. The downstream `confidence_thresholds_correct` audit check (Step 7) validates this exact mapping.

Cache the channel-wide eligible count for the duration of the run; the draft step uses it for any claim drawn from the full eligible set. Sub-population claims (e.g., "only tutorials") MUST scope their own counts and cite the sub-population `n`, not the channel-wide eligible count (per RESEARCH.md Pitfall 2, a tutorial-only claim cites `n=7`, not the channel-wide `n=18`).

Output (held in working memory for the draft step): `{eligible_count: N, total_full_length: M, latest_common_snapshot: "YYYY-MM-DD"}`.

## Step 6: Draft the report (PERSIST-01)

Compose the markdown report per `CLAUDE.md § "Report structure"`. This step implements REPORT-01 (six-section structure), REPORT-02 (numbers + age + confidence in plain sight), and the D-07 inline-parenthetical format (per `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`).

### 1. Rules to apply before writing prose

Before drafting any sentence, load the following CLAUDE.md sections and apply each rule to the data on hand:

- Apply `CLAUDE.md § "Age control is non-negotiable"`. Exclude any video with `days_since_published < 14` from top-performer claims and pattern claims. If such a video is mentioned at all, flag it as low-confidence and say so inline. Cross-age comparisons use the first-30-day window when possible. When the data does not support a strict first-30-day window, use the `views_per_day_since_publish_proxy` from `sql/03_age_controlled_performance.sql` and label it as a proxy explicitly per that SQL file's own IMPORTANT header comment block. "Trending up" or "declining" requires at least 14 days of data per video in the comparison set.
- Apply `CLAUDE.md § "Small samples get hedged, every time"`. Use the `eligible_count` from Step 5 to assign the channel-wide confidence label per the threshold table in that section (`< 5` low, `5 to 10` moderate, `>= 10` standard; boundaries verified in Step 5). For sub-population claims, scope `n` to that sub-population. A tutorial-only claim cites the tutorial-only count (e.g., `n=7`), not the channel-wide `eligible_count` (e.g., `n=18`). See RESEARCH.md Pitfall 2.
- Apply `CLAUDE.md § "Brutal honesty about underperformance"`. Wins and misses get equal weight; do not bury weak results in caveats; name videos and numbers plainly. A recent bet that did not land gets named as not landing.
- Apply `CLAUDE.md § "Never claim what the data does not support"`. Distinguish observed (in the query result), inferred (a reasonable read), and assumed (a guess being flagged). If data did not move enough to be meaningful at this sample size, say so. If a query returned no rows or suspicious rows, report that instead of analyzing around it.
- Apply `CLAUDE.md § "Voice"`. First-person plural where it fits ("we tried", "what we are seeing"). No em dash (U+2014). No en dash (U+2013) as punctuation. No banned vocabulary from the project CLAUDE.md list (delve, leverage, robust, seamless, navigate, underscore, showcase, tapestry, realm, multifaceted, transformative, testament to). No formulaic openers or closers ("Great news!", "Overall,", "In conclusion,"). No contrastive reframes ("It's not X, it's Y"; "Not just X but Y"). Vary sentence length.
- Apply D-08 from `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`. The prior reports read in Step 4 are calibration memory, not reader memory. Do not cite them in prose. Cross-week framing per D-09 is allowed only when self-contained (e.g., `"For the third consecutive week, X has held."`). Banned phrases: `"as we said last week"`, `"as noted previously"`, `"the prior report"`, `"this continues the trend we observed"`.

### 2. Confidence label format (per D-07)

For prose claims, end the sentence with ` (label, n=N).` where `label` is one of `low confidence`, `moderate confidence`, `standard confidence`. The `n=N` is the count of *eligible* videos in the comparison set the claim drew from (Step 5's channel-wide `eligible_count` for channel-wide claims, or the sub-population count for scoped claims). Example from RESEARCH.md Pattern 5:

```
VID042 "GraphQL vs REST" pulled 4,300 views in its first 30 days, about 5x the channel median of 860 (standard confidence, n=18).
```

For table-shaped claims, add `Confidence` and `n` columns to the table; do not inline the parenthetical inside cells (D-07). Example:

| Video | Views (first 30d) | vs. median | Confidence | n |
|-------|-------------------|------------|------------|---|
| GraphQL vs REST | 4,300 | 5x | standard | 18 |

**D-07a (single claim, single label):** Do not emit per-section header confidence blocks. Different claims in the same section may carry different labels. The label rides with the claim it qualifies, one label per claim.

**D-07b (no Notion callout for confidence labels):** Confidence labels render as plain text through whatever Notion blocks the Skill emits. Notion callouts are reserved for the stale-data flags from the Phase 1 Data Health section; do not wrap confidence parentheticals in callouts.

### 3. Six-section structure (REPORT-01, D-11)

The report renders all six sections in this order, with this heading text exactly:

- `## Data Health` (already produced by Step 2; render verbatim from the parsed `sql/04` output. No analyst commentary added here unless `stale_tables` is non-empty, in which case the section adds one line per stale table naming the staleness in days.)
- `## Headline` (one or two sentences capturing the most important finding of the week. Lead with the finding; no preamble.)
- `## What is working` (two to four findings with numbers, age context, and inline confidence labels. Exclude any video with `days_since_published < 14`; if such a video is mentioned, low-confidence flag applies.)
- `## What is not working` (same shape as What is working. Do not skip this section if results are not dramatic; smaller misses still matter per CLAUDE.md § "Brutal honesty about underperformance".)
- `## Patterns worth watching` (early signals labeled with confidence; multi-week framing per D-09 allowed when self-contained.)
- `## Open questions` (things the data hints at but cannot answer.)

Every section heading renders, every time (D-11). Empty-section bodies use one of these explicit forms:

- `Nothing material to report this week.` when the data was available but no finding meets the confidence bar.
- `{Topic} analysis unavailable: {table} is {N} days stale (see Data Health).` when the section depended on a stale table.

Never silently omit a heading. Never pad with weak findings to fill a section.

### 4. Stale-table disclaimer rule (D-12)

If a finding would have drawn from a table flagged as stale by the Step 2 data-health check (i.e., the table appears in `stale_tables`), replace the finding with a one-line disclaimer that names the table and the staleness in days, and points to Data Health. Do NOT compute against stale data.

When multiple findings in the same section would all disclaim the same stale table, collapse to ONE disclaimer per section. Example:

```
Watch-time and traffic-source analysis is unavailable: daily_video_analytics is 89 days stale (see Data Health).
```

Then list whatever non-stale-dependent findings are present in the same section, if any. This is RESEARCH.md Pitfall 5 (stale-table disclaimer pile-up); the per-section collapse keeps the report from reading as 60% disclaimer and 40% analysis when two tables are stale.

The `SIMULATE_STALE` env-var (Step 2) is the testing path for this rule when no real stale state exists in BigQuery. The first Phase 2 run against live data will exercise the rule only if real staleness is present or `SIMULATE_STALE` was set at run time.

### 5. Per-section drafting guidance

- **Data Health:** render the per-table table from Step 2's parsed sql/04 result. If `stale_tables` is non-empty, follow with one line per stale table naming the staleness in days. If empty, follow with one sentence stating all four tables are within the 3-day freshness contract.
- **Headline:** one or two sentences. Lead with the finding the reader should remember. Do not open with a preamble or a status update.
- **What is working:** two to four findings drawn from `sql/02` (top videos) and `sql/03` (age-controlled). Each finding includes the video title, the number being cited, the `days_since_published` for age context, and an inline `(label, n=N).` parenthetical. If `daily_video_stats` is stale, the section starts with the D-12 disclaimer for that table.
- **What is not working:** findings about videos that underperformed comparable peers. Use the same shape as What is working. Apply CLAUDE.md § "Brutal honesty about underperformance" plainly. Do not soften.
- **Patterns worth watching:** early signals labeled with confidence; multi-week framing per D-09 is allowed if self-contained. If the channel-wide `eligible_count` is below 5, default every pattern claim in this section to `low confidence` per the CLAUDE.md threshold table; if `daily_video_analytics` or `daily_traffic_sources` is stale, most pattern claims will land as D-12 disclaimers.
- **Open questions:** things the data hints at but cannot answer; useful for next week's analysis or for a manual look.

### 6. Output dict (NOTION-02)

The draft step ends by assembling the structured report dictionary the existing `write-notion-report` Skill invocation step consumes. Per PHASE1-ASSUMPTIONS-VERIFIED.md A2: Phase 1's Skill renders Notion blocks from `markdown_body` only and the per-finding `confidence` field on `working[]` / `not_working[]` / `patterns[]` entries is a plain string (`"low" | "moderate" | "standard"`), not a structured `{label, n}` dict. Plan 02-02 keeps the markdown-rendering path: place the full `(label, n=N).` parenthetical inline in the prose (inside `markdown_body` and inside each entry's `body` string), and populate the entry-level `confidence` field with the label string only. The `n` lives in the prose. A future Skill enrichment can promote `confidence` to `{label, n}` without breaking this contract.

Write the assembled markdown to `reports/{run_date}.md`. Also copy the same content to `runs/{run_date}/report.md` per the folder layout in `runs/README.md`.

## Step 7: Self-audit (run AFTER draft is assembled, BEFORE invoking write-notion-report)

This step implements D-01 Layer 2 from `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`: Step 6 made the rules explicit at draft time (Layer 1); this step verifies the rules were actually followed. Without it, the draft step still depends on the analyzer remembering to apply the voice rules; with it, every run gates publish on a copy-into-response checklist and the audit trail makes silent voice violations visible after the fact. Run AFTER Step 6 (draft assembled, markdown written to `reports/{run_date}.md`) and BEFORE Step 8 (assemble the report dict for `write-notion-report`).

The pattern is the copy-into-response checklist from Anthropic's Skill best practices (cited in `.planning/phases/02-honest-analyst-depth/02-RESEARCH.md` § "Common Pitfalls" 3): literally copy the checkbox list below into the working response and tick each item as the draft is walked. The checklist mirrors `CLAUDE.md` and `02-CONTEXT.md` rules 1:1, referenced by section title so future `CLAUDE.md` edits flow through by re-derivation, not parallel maintenance.

### Checklist (copy into the response and tick each item)

```
Self-audit progress:

Structural checks (REPORT-01 / D-11 / D-12):
- [ ] Six sections present in order: Data Health, Headline, What is working, What is not working, Patterns worth watching, Open questions.
- [ ] Every section heading renders. Sections with no findings carry an explicit "Nothing material to report this week." line OR a stale-table disclaimer (D-11).
- [ ] Any section that would have drawn from a stale table (per Data Health) carries a one-line disclaimer naming the table and staleness (D-12). When multiple findings would disclaim the same table, the disclaimers are collapsed to one per section (RESEARCH.md Pitfall 5).

Age-control checks (ANALYSIS-01 / ANALYSIS-04, per CLAUDE.md § "Age control is non-negotiable"):
- [ ] No video with days_since_published < 14 appears in "What is working" top-performer claims.
- [ ] Cross-age comparisons use a first-30-day window OR are explicitly labeled as a views_per_day_since_publish_proxy per sql/03's IMPORTANT header comment.
- [ ] Trending claims gated on at least 14 days of data per video in the comparison set.

Confidence-label checks (ANALYSIS-03 / REPORT-02, per CLAUDE.md § "Small samples get hedged, every time"):
- [ ] Every pattern claim ends with (label, n=N) parenthetical OR appears in a table with Confidence and n columns (D-07).
- [ ] Each n cited matches the comparison set the claim actually drew from (RESEARCH.md Pitfall 2: a tutorial-only claim cites the tutorial-only n, not the channel-wide eligible_count).
- [ ] Labels match CLAUDE.md § "Small samples get hedged, every time" thresholds: n < 5 -> low confidence, n=5 to 10 -> moderate confidence, n >= 10 -> standard confidence.

Voice checks (REPORT-03, per CLAUDE.md § "Voice"):
- [ ] No em dashes (U+2014) anywhere in the draft.
- [ ] No en dashes (U+2013) used as punctuation.
- [ ] None of the banned vocabulary from CLAUDE.md § "Voice" appears. The authoritative list lives in that section (currently: delve, leverage, robust, seamless, navigate, underscore, showcase, tapestry, realm, multifaceted, transformative, testament to). Re-read the section at audit time; the list there is authoritative even if it evolves.
- [ ] No formulaic openers or closers: no "Great news!", "Great question!", "Overall,", "In conclusion,", "Ultimately,", no contrastive "Not X, but Y" reframes, no opening transitions like "Moreover,", "Furthermore,", "Additionally,".
- [ ] First-person plural ("we tried", "what we are seeing") used where it fits, per CLAUDE.md § "Voice" ("Kyle and the audience are figuring this out together"). A draft written entirely in third person or marketing-impersonal voice fails this check even if every other voice item passes.

Prior-report citation checks (D-08 / D-09, per CLAUDE.md § "Report structure"):
- [ ] No prior-report citations in prose. Banned phrases: "as we said last week", "as noted previously", "the prior report", "this continues the trend we observed". (The bare phrase "as noted" is intentionally excluded from this list to avoid false-positives on legitimate prose like "as noted in the data"; "as noted previously" above already catches the prior-report case.)
- [ ] Multi-week claims (if any) stand on their own without requiring the reader to have seen a prior report (D-09 example: "For the third consecutive week, X has held." is allowed).

Provenance check (per CLAUDE.md § "Verification & Evidence"):
- [ ] Numbers cited in the draft are present in the underlying runs/{run_date}/queries/*.json files. Spot-check three randomly chosen claims by grepping the value in the queries directory.
```

### Recording the audit trail

The checklist's purpose is dual: gate the publish, and leave a machine-readable audit trail. For each item:

- **For each PASSED check:** append the canonical check identifier (snake-case names listed below) to `summary.json.voice_audit.checks_passed` (held in working memory until Step 10 writes summary.json).
- **For each FAILED check:** fix the violation inline in the draft (edit `reports/{run_date}.md` and the corresponding `markdown_body` string in working memory; do not advance to the assemble-dict step until the fix is applied), then append a structured entry to `summary.json.voice_audit.fixes_applied` with shape `{"section": "<section name>", "fix": "<one-line description of what was changed>"}`. Example: `{"section": "Patterns worth watching", "fix": "Replaced em dash with comma in framing of tool-tutorials trend"}`.

### Canonical check identifiers

These are the snake-case names to use in `voice_audit.checks_passed`:

- `six_sections_in_order`
- `empty_sections_render_with_explicit_body`
- `stale_table_disclaimers_present`
- `age_control_enforced`
- `cross_age_window_labeled`
- `trending_claims_have_minimum_age`
- `confidence_labels_present`
- `confidence_n_matches_comparison_set`
- `confidence_thresholds_correct`
- `no_em_dashes`
- `no_en_dashes_as_punctuation`
- `no_banned_vocab`
- `no_formulaic_openers`
- `first_person_plural_where_it_fits`
- `no_prior_report_citation`
- `multi_week_claims_self_contained`
- `numbers_match_underlying_query_results`

### Publish gate (RESEARCH.md Pitfall 3 mitigation)

When all checks pass, proceed to Step 8 (Assemble the report dict) and from there to Step 9 (Invoke `write-notion-report`). Do NOT advance to the assemble-dict step while any item remains unticked. The Skill SHOULD NOT be invoked while any item remains unticked.

**Enforcement is honor-system, not code.** The gate is markdown instructions to the analyzer agent, not a runtime check. Two consequences:
- "SHOULD NOT" (not "MUST NOT") accurately describes the strength of enforcement here. A future Python-side validator could promote this to a hard MUST (TODO: surface `voice_audit` presence as a precondition in a wrapper script around Step 9), but until that lands the strongest available enforcement is the agent's compliance with this recipe.
- **Step 9 precondition (markdown gate, layer 2):** before invoking `write-notion-report` in Step 9, re-verify that `voice_audit.checks_passed` is non-empty in working memory. If it is empty or missing, return to Step 7 and run the audit. This second instruction means the agent must violate TWO explicit recipe steps to skip the audit, not one.

If a check cannot be ticked because the data needed to verify it is unavailable or because the case genuinely falls outside the checklist's scope, record the reason in `summary.json.voice_audit.fixes_applied` with `section: "(audit)"` and `fix: "could not verify <check_identifier>: <reason>"`, and proceed only if the reason is genuinely outside the checklist's scope. Do not use this escape hatch to skip checks that could be verified with a little more work.

A missing or empty `summary.json.voice_audit` block after a successful run indicates the self-audit step did not execute. That is visible after the fact even though enforcement is markdown, not code; it is itself a finding for the next run's analyst to investigate.

## Step 8: Assemble the report dict

Build a strict 8-key dict matching the `write-notion-report` Skill's input contract (defined in `.claude/skills/write-notion-report/SKILL.md`):

- `run_date`: string `YYYY-MM-DD` (from Step 0).
- `data_health`: `{"snapshot_dates": {table: date}, "stale_tables": [string, ...]}` (both built in Step 2).
- `headline`: 1-2 sentence string from the headline drafted in Step 6.
- `working`: list of `{title, body, confidence}` dicts. In Phase 1 this has exactly one entry (the top-videos finding from Step 3), with `confidence: "low"` per CONTEXT.md (this is a raw top-N reading, not a pattern claim).
- `not_working`: `[]` (Phase 2 wires this).
- `patterns`: `[]` (Phase 2 wires this).
- `open_questions`: `[]` (Phase 2 wires this).
- `markdown_body`: the full report markdown from Step 6.

Validate before Step 9: if any key is missing, do NOT invoke the Skill. Record `errors: [{"category": "report_dict_invalid", "message": "missing key: <name>", "step": "assemble_dict"}]`, set `notion_write_ok = false` in working memory (Step 9 will not execute, so the Step 10 schema field needs an explicit default), and proceed to Step 10 to write summary.json.

## Step 9: Invoke write-notion-report (NOTION-01..06)

**Precondition (markdown gate per Step 7):** before invoking the Skill, confirm `voice_audit.checks_passed` in working memory is non-empty. If it is empty or missing, Step 7 did not run; return to Step 7 and complete the audit before continuing. Do not invoke the Skill on an unaudited draft.

Invoke the `write-notion-report` Skill with the assembled dict. The Skill returns one of:

- `{"ok": true, "page_id": "<uuid>", "url": "<notion url>"}` on success.
- `{"ok": false, "error": "<string>", "category": "<env_missing|parent_not_found|permission_denied|transport_error|unknown>"}` on failure.

Capture the return value. CRITICAL: do NOT fail the run if the Skill returns `ok: false`. Local artifacts already exist from the data-health, top-videos, eligible-count, prior-report, and draft steps; the write-summary step captures the Skill's failure in summary.json. The report has landed in `reports/{run_date}.md` regardless.

If the Skill is not loaded in the session (the `.claude/skills/write-notion-report/SKILL.md` file is missing or the runtime did not pick it up), treat as `{"ok": false, "category": "skill_unavailable"}`, queue the operator message naming docs/runbook.md section "Notion write failed", and proceed to the write-summary step.

## Step 10: Write summary.json (PERSIST-02, ERR-02)

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
- `notion_write_ok`: boolean from Step 9, or `false` if Step 9 was skipped due to a Step 8 dict-validation failure (`report_dict_invalid` error category). The field MUST always be present; an undefined `notion_write_ok` makes the Step 11 operator-message selection (SUCCESS vs. NOTION-FAIL vs. BQ-FAIL) ambiguous.
- `voice_audit`: `{"checks_passed": [string, ...], "fixes_applied": [{"section": string, "fix": string}, ...]}` from Step 7's self-audit. Both arrays MAY be empty if the audit ran cleanly and nothing needed fixing (improbable on early runs), but the `voice_audit` key itself MUST be present whenever Step 7 ran. A missing `voice_audit` after a successful run indicates Step 7 did not execute.
- `notion_page_id`, `notion_url`: from the Skill-invoke step's success path; omit or set null on failure.
- `prior_reports_consulted`: JSON array of `YYYY-MM-DD` strings recording which prior `reports/{date}.md` files were read during the prior-report calibration step (D-10). MAY be empty (`[]`) if fewer than three prior reports exist or none were consulted.
- `errors`: list (may be empty); each entry `{"category": ..., "message": ..., "step": ...}`.
- `warnings`: list (may be empty); each entry is a human-readable string. Used for non-fatal events that an auditor should see (e.g., `simulate_stale_applied: ...`, `arguments_ignored: ...`).

PERSIST-03 contract: the write order is queries -> report -> Skill -> summary.json LAST. If any earlier step throws, this step still runs. Implementation: after each step that succeeds, append the cumulative state to `runs/{run_date}/.partial-state.json` (transient file, dot-prefixed). If any step throws, this step reads `.partial-state.json`, merges in the captured error, writes the final `summary.json`, and deletes the partial file. The partial file lives only between throw and the write-summary step; it is never committed.

Always write summary.json. Never skip it. This is the ERR-02 contract.

## Step 11: Operator message

Print exactly one of three patterns, then exit:

- SUCCESS: `Run {run_date} complete. Notion: {url}. Local: reports/{run_date}.md`
- NOTION-FAIL: `Run {run_date} complete locally but Notion write failed: {category}. Recovery: see docs/runbook.md § 'Notion write failed'. Local: reports/{run_date}.md`
- BQ-FAIL: `Run {run_date} FAILED at {step}: {error}. Recovery: see docs/runbook.md § '{relevant section}'.`

The three patterns are exhaustive: every run finishes with one of them. For BQ-FAIL, the relevant docs/runbook.md section is one of "BigQuery auth failure", "Required table is missing or empty", or "A required table is stale", chosen by the error category recorded in Step 2 or Step 3.
