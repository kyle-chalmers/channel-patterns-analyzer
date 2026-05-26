# Runbook

What to do when the analyzer fails. One section per failure mode. Each section: how to recognize it, what to do, where to record it.

If you hit a failure mode that isn't here, add it as part of the fix. The runbook only helps if it stays current.

---

## BigQuery auth failure

**Symptom.** `bq query` returns `Could not load the default credentials` or `Reauthentication is needed`. The analyzer's first SQL call errors out.

**Fix (local).**

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project "$BQ_PROJECT"
```

Then re-run the analyzer.

**Fix (scheduled cloud routine).** The routine uses the BigQuery web connector authorized in your Anthropic account, not a long-lived credential file. If the connector is the issue, see § "BigQuery MCP connector not authorized" below. The routine has no `bq` or `gcloud` CLI; do not look for missing local-auth state. See `docs/schedule.md` § "Local vs. cloud" for the cloud-vs-local distinction.

**Recording.** If credentials expired on a known cadence, note the next expiry in `CHANGELOG.md` so future-you isn't surprised.

---

## A required table is stale

**Symptom.** The Data Health section of the report flags a table whose latest `snapshot_date` is older than `CURRENT_DATE() - 3` (per `BUSINESS_RULES.md` § "Data health expectations").

**What the analyzer should do.** Surface staleness at the top of the report and label any downstream finding that depends on the stale table. Do not silently produce a report that quietly relies on stale data.

**Upstream check.** The data is loaded by the [youtube-bigquery-pipeline](https://github.com/kyle-chalmers/youtube-bigquery-pipeline) repo (see README). If a table is stale, the failure is almost always upstream. Check that pipeline's last run and any error logs there before assuming the analyzer is at fault.

**Recording.** If a table is stale for more than one week, file it in `CHANGELOG.md` as a known data gap with the dates affected.

---

## Required table is missing or empty

**Symptom.** `bq query` returns "Not found: Table …" or returns zero rows for a query that should never be empty. The recipe records `category: missing_table` or `category: empty_result` in `summary.json.errors[]`.

**What the analyzer should do.** Stop. Report the missing/empty table in the Data Health section. Do not invent a report from the tables that do exist.

**Fix.** Verify the dataset name (`BQ_DATASET`, defaults to `youtube_analytics`) and the table list in `BUSINESS_RULES.md` § "Table grain and join keys (data contract)" still match what's in BigQuery. If the upstream pipeline renamed something, update `sql/` and add a `CHANGELOG.md` entry.

**Recording.** Log the affected table and the date the analyzer first noticed the miss.

---

## BigQuery schema drift

**Symptom.** A query references a column that no longer exists, or a join produces unexpected cardinality (row count balloons or collapses).

**What to do.**

1. Re-read `BUSINESS_RULES.md` § "Table grain and join keys (data contract)" and compare against the current BigQuery schema (`bq show --schema <dataset>.<table>`).
2. If the schema genuinely changed upstream, update `sql/`, update `BUSINESS_RULES.md` § "Table grain and join keys (data contract)", and add a `CHANGELOG.md` entry naming the schema change and which queries were touched.
3. If the schema didn't change but a query is wrong, that's a code fix in `sql/` only. Still log it in `CHANGELOG.md` if it would change a future report's numbers.

**Don't silently coerce types or swallow new columns.** The whole analyzer is built on the assumption that the data contract is stable; drift should be loud.

---

## Notion write failed

**Symptom.** The `write-notion-report` skill returns an error: page-not-found, permission-denied, MCP server unreachable, etc. The recipe records `category: parent_not_found`, `category: permission_denied`, or `category: transport_error` in `summary.json.errors[]`.

**What the analyzer should do.** Surface the error with enough detail for the operator to fix it: the Notion page ID being written to, whether the run was using local MCP vs. the web connector, and the underlying error message.

**Fix (local MCP).** Reinstall or restart the Notion MCP server (see [notion.com/integrations](https://www.notion.com/integrations)). Confirm the integration still has access to the target page (Notion sometimes silently removes access when a workspace owner changes settings).

**Fix (web connector / cloud routine).** Re-authorize the Notion connector in your Anthropic account at [claude.com](https://claude.com). Confirm `NOTION_REPORT_PAGE_ID` is still valid and the connector has access. For the cloud-routine variant where the connector is missing entirely from the session, see § "Notion connector not authorized" below.

**Recovery.** Even if the Notion write fails, the report should still land in `reports/{run_date}.md` and the run folder in `runs/{run_date}/` so the work isn't lost. Re-publishing to Notion is a separate manual step.

---

## Required environment variable is missing

**Symptom.** The `/run-analyzer` recipe stops at Step 0 preflight with `errors: [{"category": "env_missing", "message": "<NAME> not set", "step": "preflight"}]` in `runs/{run_date}/summary.json`. The recipe never reaches the BigQuery transport probe. For invalid (rather than missing) values, the recipe records `category: env_invalid` from the Step 0 step-5 dataset-identifier check.

**Which variable, and how to fix it.**

- `NOTION_REPORT_PAGE_ID`. Open the channel-patterns parent page in Notion, copy the page ID from the URL (`notion.so/<workspace>/<page-id>`, the `<page-id>` portion), and add it to `.env` (gitignored). Both dashed and undashed UUID forms are accepted.
- `BQ_PROJECT`. Run `gcloud config set project <id>` to set it for the active gcloud config, or set `BQ_PROJECT=<id>` explicitly in `.env`. The recipe reads from `.env` first.
- `BQ_DATASET`. Defaults to `youtube_analytics` if unset. Set it in `.env` only if the dataset is named differently. The recipe rejects `BQ_DATASET` values that fail the BigQuery identifier regex (`^[A-Za-z_][A-Za-z0-9_]*$`) with `category: env_invalid`.

For the cloud-routine variant (the var is missing from the routine config, not the local `.env`), see § "Routine environment variable missing in cloud config" below.

**What the analyzer does.** Writes a minimal `runs/{run_date}/summary.json` with the `env_missing` or `env_invalid` error so the audit trail still exists, surfaces an operator message pointing here, and stops. No queries run, no Notion call, no report drafted.

**Recording.** If the missing variable points to a setup-doc gap (the operator could not figure out which value to use from the project docs), file a `CHANGELOG.md` entry naming the doc that needs to be expanded.

---

## BigQuery MCP connector not authorized

**Symptom.** A cloud-routine session has no `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly` tool loaded. Recipe Step 1 falls through to the `no_bigquery_transport` error because the cloud routine has no `bq` CLI either. `summary.json.errors[]` carries `category: no_bigquery_transport`.

**Fix.** Open [claude.com](https://claude.com), Settings, Connectors. Verify Google Cloud BigQuery is connected. If it shows as expired or not connected, re-authorize it. Confirm the connector's permissions include access to the project named in `BQ_PROJECT`. Re-run the routine via "Run now" in the routine's detail page.

**Recording.** If connector auth ever expires on a cadence, note the next expiry in `CHANGELOG.md`. No expiry cadence is known today.

---

## Notion connector not authorized

**Symptom.** A cloud-routine session returns `{ok: false, category: "transport_error"}` (or `permission_denied`) from the Skill invocation, and the run transcript shows the Notion tool was either missing or returned an auth-style error. Recipe Step 9 surfaces the NOTION-FAIL operator message. This is distinct from the "Notion write failed" section above, which covers the broader local-MCP-and-connector failure surface; this section is the cloud-only "connector missing from the session" case.

**Fix.** Open [claude.com](https://claude.com), Settings, Connectors. Re-authorize Notion. Confirm the integration has access to the parent page named by `NOTION_REPORT_PAGE_ID`. Re-run the routine via "Run now".

**Recording.** Same as § "Notion write failed". If connector reauthorization becomes a recurring need, log the cadence in `CHANGELOG.md`.

---

## Routine environment variable missing in cloud config

**Symptom.** `summary.json.errors[]` records `category: env_missing` from a cloud-routine session. The local `.env` is fine; the routine's per-routine environment configuration didn't include the var. The recipe stops at Step 0 preflight with no queries run.

**Fix.** Open the routine in [claude.com](https://claude.com), Routines, channel-patterns-analyzer. Click the cloud icon below the Instructions box, then the settings icon, then Environment variables. Add the missing var. The four env vars the analyzer reads are listed in `.env.example`; reference it when adding to the routine. Re-run via "Run now".

**Recording.** If the same var is missing on multiple runs, the routine config drifted from `.env.example`. File a `CHANGELOG.md` entry naming the drift.

---

## Routine run timed out or hung

**Symptom.** The Anthropic UI shows the run as not-completed after an unusually long duration. No `summary.json` lands in the repo if the recipe didn't reach Step 10.

**Fix.** Open the run transcript in the Anthropic UI. Look for hung tool calls (long BigQuery queries, network slowness in connector calls, the Skill invocation stuck). Cancel the run from the UI if needed. If the BigQuery query at Step 3 is the bottleneck, consider whether a `LIMIT` should be pushed into the SQL (the recipe currently relies on the 100-row bq default; see the Step 1 invocation-shapes note in `.claude/commands/run-analyzer.md`). Re-run via "Run now" after the cause is addressed.

**Recording.** If the same timeout recurs, file a `CHANGELOG.md` entry naming the recipe step and the observed duration. A repeating timeout at the same step usually indicates a real performance regression rather than a transient network blip.

---

## Anthropic UI shows error before recipe runs

**Symptom.** The routine session ends with an infrastructure error before the recipe's first step executes. No `summary.json` at all; no queries, no report.

**Fix.** Open the run transcript and read the bottom-of-session error. Common causes:

1. Repo clone failed (GitHub auth issue with the connected repo). Re-check the Repositories field in the routine config and confirm `kyle-chalmers/channel-patterns-analyzer` is selected and reachable.
2. Network policy blocked an outbound call. The routine's Environment is set to `Default` per the `docs/schedule.md` walkthrough. Verify the Default environment's network policy hasn't changed.
3. Claude Code's cloud environment itself is unavailable. Check the Anthropic status page before assuming the routine is broken.

Re-run via "Run now" once the cause is addressed.

**Recording.** Infrastructure errors get a `CHANGELOG.md` entry with the date and the error excerpt so the pattern is visible across runs.

---

## How to test the stale-data path without real stale data

This is an operator note, not a failure mode. Use it when the runbook's stale-table machinery (D-12 disclaimer rule) needs to be exercised but every analytics table is fresh.

**Why this exists.** The 89-day stale state on `daily_video_analytics` and `daily_traffic_sources` resolved on 2026-05-25, so there is no live way to hit the disclaimer rule end-to-end without a seam.

**How.** Set `SIMULATE_STALE` and re-run the analyzer. Example:

```bash
SIMULATE_STALE="daily_video_analytics:89,daily_traffic_sources:89" claude
> "Run the analyzer."
```

The override mutates the in-memory `data_health` rows at recipe Step 2 (lines 51 to 59 of `.claude/commands/run-analyzer.md`). The on-disk `runs/{date}/queries/data_health.json` keeps the real values for the audit trail; the synthetic staleness lives in working memory only.

**Recording.** `summary.json.warnings` will contain `simulate_stale_applied: <value>` so the audit trail shows the data was synthetic. No `CHANGELOG.md` entry needed for individual test runs; the override exists precisely to be invoked freely.

---

## Skill input dict missing a required key

**Symptom.** `summary.json.errors[]` records `category: report_dict_invalid` with a message naming the missing key. Recipe Step 8 caught the mismatch before invoking the Skill, so the Skill was never called and Notion write was skipped.

**Fix.** Read the error entry's message and identify which key is missing. Open `.claude/skills/write-notion-report/SKILL.md` for the 8-key input contract (`run_date`, `data_health`, `headline`, `working`, `not_working`, `patterns`, `open_questions`, `markdown_body`). Find which Step in the recipe should have produced that key, and check whether the prior step actually wrote the value to working memory. The most likely cause is a refactor that changed key names in one place but not the other.

**Recording.** If the missing key is a schema drift between the recipe and the Skill, fix both files and add a `CHANGELOG.md` entry naming the contract change. A recipe-Skill contract drift is exactly the kind of silent failure the audit trail exists to catch.

---

## write-notion-report Skill not loaded in the session

**Symptom.** `summary.json.errors[]` records `category: skill_unavailable` (or, equivalently for the cloud routine, `category: transport_error` with a message about the Skill not being loaded). Recipe Step 9 couldn't find the Skill at invocation time.

**Fix (local).** Confirm `.claude/skills/write-notion-report/SKILL.md` exists in the repo and the runtime picked it up. Restart Claude Code in the repo directory so the Skills directory is rescanned on session start.

**Fix (cloud routine).** Verify the Repositories field in the routine config includes `channel-patterns-analyzer` so the cloned repo carries the `.claude/skills/` folder. If the repo is selected but the Skill still doesn't load, the cloud runtime may have missed the Skills directory on clone; open a fresh routine run with "Run now" and check the early transcript lines for Skills loading.

**Recording.** If the Skill consistently fails to load in a particular session shape, file a `CHANGELOG.md` entry naming the session type. Skill loading is a runtime contract that the audit trail should be able to reconstruct after the fact.

---

## No BigQuery transport available

**Symptom.** `summary.json.errors[]` records `category: no_bigquery_transport` from recipe Step 1. The recipe found neither the `bq` CLI on PATH nor the BigQuery MCP tool loaded in the session, and `DATA_SOURCE=csv` was not set.

**Fix (local).** Install the `gcloud` SDK and authorize `bq` per § "BigQuery auth failure" above, OR ensure the BigQuery MCP connector is enabled in the local session. The recipe will auto-detect whichever is available.

**Fix (cloud routine).** The cloud routine has no `bq` CLI installed; the BigQuery connector is the only data path. Verify the BigQuery connector is authorized in your Anthropic account, see § "BigQuery MCP connector not authorized" above.

**Fix (CSV mode).** If you intended to run in CSV mode, set `DATA_SOURCE=csv` in `.env` before re-running. The recipe will short-circuit the BigQuery probe and read from `sample_data/*.csv` instead.

**Recording.** If the local setup needs documentation, expand the README's setup section. The cloud variant should already be covered by `docs/schedule.md` § "Cloud routine setup walkthrough"; if it isn't, file a `CHANGELOG.md` entry and add the missing step.

---

## Report says something the operator believes is wrong

**Symptom.** A claim in the published report doesn't match Kyle's reading of the channel.

**Investigate.**

1. Open `runs/{run_date}/summary.json` to confirm which snapshot dates were used and whether anything was flagged stale.
2. Open `runs/{run_date}/queries/` to see the raw rows the analyzer reasoned over. If the rows support the claim, the issue is interpretation. If they don't, the issue is the analysis prompt or the SQL.
3. If the issue is interpretation (the rules in `CLAUDE.md` or `BUSINESS_RULES.md` produced an unwanted reading), update the rules and add a `CHANGELOG.md` entry. Don't patch a single report.
4. If the issue is SQL, fix the query and log the change.

The audit trail in `runs/` exists precisely for this case.
