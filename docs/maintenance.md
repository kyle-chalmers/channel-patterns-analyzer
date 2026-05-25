# Maintenance

How to extend the analyzer without breaking the contract it has with the operator (and the audience).

## Adding a new SQL query

1. Add the file to `sql/` with a numeric prefix (`05_*.sql`, `06_*.sql`) so the run order stays obvious.
2. Reference the dataset by `BQ_DATASET` (default `youtube_analytics`) — don't hardcode a project.
3. If the query touches a table whose grain or join keys aren't already covered in `BUSINESS_RULES.md` §6, extend §6 first and reference it from the query's comment header.
4. Make sure the query, when its result is dumped to JSON, stays small enough to commit (~hundreds of KB is fine, multi-MB is not). The dataset is small for now — revisit if a query ever returns thousands of rows.
5. Add the file to the list the analyzer runs each week (in `CLAUDE.md` or wherever the analyzer's query manifest lives).
6. Add a `CHANGELOG.md` entry.

## Evolving a business rule

`BUSINESS_RULES.md` is policy. Changing it changes the meaning of every future report.

1. Make the smallest possible change. If you're tempted to rewrite a section, write the new version next to the old and migrate deliberately.
2. State the change in plain language in `CHANGELOG.md`, including **before** and **after** values for any threshold you moved.
3. If the change would have changed a recent report's numbers or framing, say so in the changelog entry. Don't silently retcon.
4. Do **not** change the fiscal-year anchor (§1) without discussing — every prior report assumed July. A mid-stream change makes the archive incoherent.

## Retiring a pattern

Sometimes a "pattern worth watching" turns out to be noise. To retire it:

1. Note the date and the reason in `CHANGELOG.md` (e.g., "Retired the 'Tuesday upload bump' hypothesis — held at low confidence for 8 weeks, didn't strengthen.").
2. The analyzer reads recent reports as memory, so just not surfacing the pattern again is enough on the report side. The changelog entry is what keeps the decision auditable.

## Running the analyzer manually

For a one-off question or to test a query change without waiting for the weekly schedule:

1. Confirm BigQuery auth: `bq query --use_legacy_sql=false "SELECT 1"`.
2. Start a Claude Code session in the repo root. The `CLAUDE.md` + `BUSINESS_RULES.md` get loaded automatically.
3. Ask the analyzer to run a report.
4. The output goes to Notion as usual **and** to `reports/{today}.md` + `runs/{today}/`. If you don't want the run in the archive (e.g., you're testing a broken query), say so explicitly to the analyzer or delete the folder before committing.

## Re-running after a failure

If a scheduled run errored partway through, the analyzer should have still written `runs/{run_date}/summary.json` with the error captured. To retry:

1. Read the summary to confirm what failed.
2. Fix the underlying issue (see `docs/runbook.md`).
3. Re-run the analyzer manually. The second run's artifacts land at `reports/{run_date}-2.md` and `runs/{run_date}-2/` so the original failure stays in the audit trail.

## What you should _not_ do

- Don't delete an old report from `reports/` to "clean up." The archive is more useful with every weak-looking week left in it — that's how you see the channel's real volatility.
- Don't backfill reports. The whole archive's value is that each entry reflects what the analyzer actually knew that week.
- Don't hardcode the video count, the dataset name, or thresholds that `BUSINESS_RULES.md` already governs. If you need a value the rules don't cover, add it to the rules first.
