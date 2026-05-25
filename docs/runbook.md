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

**Fix (scheduled cloud routine).** The routine doesn't have your laptop's `gcloud` login. It needs BigQuery credentials passed as environment variables (typically a service account key). Check the routine's environment config in the Anthropic UI and confirm the service account is still valid in GCP. See `docs/schedule.md` for the cloud-vs-local distinction.

**Recording.** If credentials expired on a known cadence (e.g., 90-day service-account key rotation), note the next expiry in `CHANGELOG.md` so future-you isn't surprised.

---

## A required table is stale

**Symptom.** The Data Health section of the report flags a table whose latest `snapshot_date` is older than `CURRENT_DATE() - 3` (per `BUSINESS_RULES.md` §5).

**What the analyzer should do.** Surface staleness at the top of the report and label any downstream finding that depends on the stale table. Do not silently produce a report that quietly relies on stale data.

**Upstream check.** The data is loaded by the [youtube-bigquery-pipeline](https://github.com/kyle-chalmers/youtube-bigquery-pipeline) repo (see README). If a table is stale, the failure is almost always upstream — check that pipeline's last run and any error logs there before assuming the analyzer is at fault.

**Recording.** If a table is stale for more than one week, file it in `CHANGELOG.md` as a known data gap with the dates affected.

---

## Required table is missing or empty

**Symptom.** `bq query` returns "Not found: Table …" or returns zero rows for a query that should never be empty.

**What the analyzer should do.** Stop. Report the missing/empty table in the Data Health section. Do not invent a report from the tables that do exist.

**Fix.** Verify the dataset name (`BQ_DATASET`, defaults to `youtube_analytics`) and the table list in `BUSINESS_RULES.md` §6 still match what's in BigQuery. If the upstream pipeline renamed something, update `sql/` and add a `CHANGELOG.md` entry.

---

## BigQuery schema drift

**Symptom.** A query references a column that no longer exists, or a join produces unexpected cardinality (row count balloons or collapses).

**What to do.**

1. Re-read `BUSINESS_RULES.md` §6 — table grain and join keys — and compare against the current BigQuery schema (`bq show --schema <dataset>.<table>`).
2. If the schema genuinely changed upstream, update `sql/`, update `BUSINESS_RULES.md` §6, and add a `CHANGELOG.md` entry naming the schema change and which queries were touched.
3. If the schema didn't change but a query is wrong, that's a code fix in `sql/` only — still log it in `CHANGELOG.md` if it would change a future report's numbers.

**Don't silently coerce types or swallow new columns.** The whole analyzer is built on the assumption that the data contract is stable; drift should be loud.

---

## Notion write failed

**Symptom.** The `write-notion-report` skill returns an error: page-not-found, permission-denied, MCP server unreachable, etc.

**What the analyzer should do.** Surface the error with enough detail for the operator to fix it: the Notion page ID being written to, whether the run was using local MCP vs. the web connector, and the underlying error message.

**Fix (local MCP).** Reinstall or restart the Notion MCP server (see [notion.com/integrations](https://www.notion.com/integrations)). Confirm the integration still has access to the target page (Notion sometimes silently removes access when a workspace owner changes settings).

**Fix (web connector / cloud routine).** Re-authorize the Notion connector in your Anthropic account at [claude.com](https://claude.com). Confirm `NOTION_REPORT_PAGE_ID` is still valid and the connector has access.

**Recovery.** Even if the Notion write fails, the report should still land in `reports/{run_date}.md` and the run folder in `runs/{run_date}/` so the work isn't lost. Re-publishing to Notion is a separate manual step.

---

## Report says something the operator believes is wrong

**Symptom.** A claim in the published report doesn't match Kyle's reading of the channel.

**Investigate.**

1. Open `runs/{run_date}/summary.json` to confirm which snapshot dates were used and whether anything was flagged stale.
2. Open `runs/{run_date}/queries/` to see the raw rows the analyzer reasoned over. If the rows support the claim, the issue is interpretation. If they don't, the issue is the analysis prompt or the SQL.
3. If the issue is interpretation (the rules in `CLAUDE.md` or `BUSINESS_RULES.md` produced an unwanted reading), update the rules and add a `CHANGELOG.md` entry. Don't patch a single report.
4. If the issue is SQL, fix the query and log the change.

The audit trail in `runs/` exists precisely for this case.
