# docs/

Operator manual for the analyzer. Read these when you need to keep the analyzer running, not when you're trying to understand what it does (that's `README.md` and `CLAUDE.md` at the root).

| File | When to read |
|---|---|
| [`runbook.md`](./runbook.md) | A run failed. BQ auth broke, a table is stale, the Notion write errored, the schema drifted. |
| [`maintenance.md`](./maintenance.md) | You want to add a new SQL query, evolve a business rule, retire a pattern, or run the analyzer manually for a one-off question. |
| [`schedule.md`](./schedule.md) | You want to understand or change the weekly `/schedule` routine that fires the analyzer. |

If a failure mode isn't in `runbook.md` yet, add it as part of the fix. The runbook only stays useful if it keeps up with reality.
