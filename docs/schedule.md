# Schedule

The analyzer runs weekly via a Claude Code `/schedule` routine, Mondays at 9am Phoenix time by default. This doc describes how the routine is wired, why local-vs-cloud matters, and how to re-run manually.

## What the routine does

Each scheduled fire spins up a fresh Claude Code context, loads `CLAUDE.md` (which `@`-imports `BUSINESS_RULES.md`), and runs the analyzer end-to-end:

1. Check BigQuery freshness (Data Health).
2. Query `youtube_analytics` for the metrics needed.
3. Read the most recent 3 to 4 reports in `reports/` to calibrate confidence (see `CLAUDE.md` § Persistent structure).
4. Draft the weekly report.
5. Hand the report to the `write-notion-report` skill, which publishes to the channel-patterns Notion page.
6. Save the report to `reports/{run_date}.md` and run metadata to `runs/{run_date}/`.

## Local vs. cloud, why the distinction matters

A routine that works perfectly in a local Claude Code terminal can fail silently in the cloud, because the environments don't share state.

| Concern | Local terminal | Cloud routine |
|---|---|---|
| BigQuery auth | Your `gcloud` login | BigQuery web connector (authorized once in your Anthropic account) |
| Notion access | Local MCP server | Web connector in your Anthropic account |
| Repo access | Local clone | Repo selected in the routine config |
| Environment variables | Your shell / `.env` | Per-routine config in the Anthropic UI |

When wiring or debugging the routine, verify each row above explicitly. The most common failure is "works locally" plus "Notion write failed in the cloud", because the local MCP isn't visible to the cloud routine, only the web connector is.

## Cloud routine setup walkthrough

Run once when first wiring the routine. After that, edits use the same form (see Changing the schedule below).

1. Authorize the BigQuery and Notion connectors once. In your Anthropic account at https://claude.com, go to Settings, Connectors. Verify both BigQuery (Google Cloud) and Notion are connected. The cloud routine has no `bq` or `gcloud` CLI installed; the BigQuery connector is the only data path.
2. Open the Routines page. claude.com, Settings, Routines, New Routine.
3. Routine name: `channel-patterns-analyzer-weekly`.
4. Instructions. Paste the full contents of `.claude/commands/run-analyzer.md` into the Instructions box. The recipe is self-contained; do not edit it after pasting (edits drift from the repo source; see `docs/maintenance.md`).
5. Repositories. Select `channel-patterns-analyzer`. Required: Step 4 of the recipe reads prior reports from the cloned repo.
6. Trigger. Select Schedule, Weekly, Monday, 9:00 AM, America/Phoenix.
7. Connectors. Verify BigQuery (Google Cloud) and Notion appear under Connectors. Remove any others (Slack, Linear, etc.) that are not needed.
8. Environment variables. Open the environment's settings (the cloud icon below the Instructions box, then the settings icon, then Environment variables) and add three:
   - `NOTION_REPORT_PAGE_ID=<from your local .env>`
   - `BQ_PROJECT=<your GCP project id>`
   - `BQ_DATASET=youtube_analytics`
9. Click Create.

## Run-now checklist

Click Run now on the routine's detail page. Verify within about 3 minutes:

- [ ] (a) A new child page appears under the channel-patterns parent in Notion within 60 seconds, titled `Weekly report, {today's Phoenix date}`. If not, see `docs/runbook.md` § "Notion write failed".
- [ ] (b) The Notion page renders all six sections: Data Health, Headline, What is working, What is not working, Patterns worth watching, Open questions. Spot-check one finding for a `(label, n=N)` parenthetical; Notion should render it as plain text (not stripped, not linkified).
- [ ] (c) The Anthropic UI shows the routine run as completed (green status). Note: green means the session exited without an infrastructure error, not that the analysis succeeded. Open the run transcript and confirm no `category: ...` error lines appear.
- [ ] (d) After the cloud routine's PR merges (or you `git pull` the `claude/...` branch), `runs/{date}/summary.json` exists with `notion_write_ok: true` and an empty `errors: []` array.

If any check fails, the linked runbook section names the recovery. New failure modes (BigQuery connector not authorized, Notion connector not authorized, routine env var missing, routine timed out, Anthropic UI shows error before recipe runs) get their own runbook sections in Plan 03-04.

## Re-running manually

For ad-hoc runs (testing a query change, recovering from a failure):

```bash
cd /Users/kylechalmers/Development/channel-patterns-analyzer
claude
> "Run the analyzer."
```

`CLAUDE.md` loads automatically. The analyzer writes to Notion and to `reports/` + `runs/` as normal. If you don't want the manual run to land in the archive, say so up front.

## Changing the schedule

Edit the routine in the Anthropic UI (Routines, channel-patterns-analyzer). The cadence, time, and timezone live there, not in the repo. If the cadence changes, update this file and add a `CHANGELOG.md` entry; the rest of the docs assume "weekly."

## Reference

- [Claude Code Routines (`/schedule`)](https://code.claude.com/docs/en/routines), official docs.
- `docs/runbook.md`, what to do when a scheduled run errors.
