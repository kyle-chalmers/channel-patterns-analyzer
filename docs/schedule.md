# Schedule

The analyzer runs weekly via a Claude Code `/schedule` routine — Mondays at 9am Phoenix time by default. This doc describes how the routine is wired, why local-vs-cloud matters, and how to re-run manually.

## What the routine does

Each scheduled fire spins up a fresh Claude Code context, loads `CLAUDE.md` (which `@`-imports `BUSINESS_RULES.md`), and runs the analyzer end-to-end:

1. Check BigQuery freshness (Data Health).
2. Query `youtube_analytics` for the metrics needed.
3. Read the most recent 3–4 reports in `reports/` to calibrate confidence (see `CLAUDE.md` § Persistent structure).
4. Draft the weekly report.
5. Hand the report to the `write-notion-report` skill, which publishes to the channel-patterns Notion page.
6. Save the report to `reports/{run_date}.md` and run metadata to `runs/{run_date}/`.

## Local vs. cloud — why the distinction matters

A routine that works perfectly in a local Claude Code terminal can fail silently in the cloud, because the environments don't share state.

| Concern | Local terminal | Cloud routine |
|---|---|---|
| BigQuery auth | Your `gcloud` login | Service account key in routine env vars |
| Notion access | Local MCP server | Web connector in your Anthropic account |
| Repo access | Local clone | Repo selected in the routine config |
| Environment variables | Your shell / `.env` | Per-routine config in the Anthropic UI |

When wiring or debugging the routine, verify each row above explicitly. The most common failure is "works locally" + "Notion write failed in the cloud" — because the local MCP isn't visible to the cloud routine, only the web connector is.

## Re-running manually

For ad-hoc runs (testing a query change, recovering from a failure):

```bash
cd /Users/kylechalmers/Development/channel-patterns-analyzer
claude
> "Run the analyzer."
```

`CLAUDE.md` loads automatically. The analyzer writes to Notion and to `reports/` + `runs/` as normal. If you don't want the manual run to land in the archive, say so up front.

## Changing the schedule

Edit the routine in the Anthropic UI (Routines → channel-patterns-analyzer). The cadence, time, and timezone live there, not in the repo. If the cadence changes, update this file and add a `CHANGELOG.md` entry — the rest of the docs assume "weekly."

## Reference

- [Claude Code Routines (`/schedule`)](https://code.claude.com/docs/en/routines) — official docs.
- `docs/runbook.md` — what to do when a scheduled run errors.
