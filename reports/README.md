# Reports archive

One markdown file per weekly analyzer run, named by **run date** (the date the analyzer fired, not the data snapshot date inside it).

```
reports/
  2026-05-24.md    ← report from the run on 2026-05-24
  2026-05-31.md
  ...
```

Each file is the same report the analyzer publishes to Notion — saved here so the archive is browsable from the repo without needing Notion access, and so the analyzer can read its own prior runs to calibrate confidence.

## How the analyzer uses this folder

Before drafting a new report, the analyzer reads the most recent 3–4 entries to:

- Avoid restating findings verbatim. If a pattern is still true, fresh-frame it.
- Upgrade or downgrade confidence labels as the sample grows.
- Notice regressions — a top performer last month that no longer is.

This does **not** break the standalone-tone rule in `CLAUDE.md`. The reports themselves stay self-contained ("assume Kyle has not seen the previous week's report"). The archive is the analyzer's memory, not the reader's.

## File naming

- Steady state: `YYYY-MM-DD.md` (one per week).
- Same-day re-run after fixing an error: `YYYY-MM-DD-2.md`, `YYYY-MM-DD-3.md`. Rare.

## Related

- `runs/{YYYY-MM-DD}/` — machine-readable audit trail for each run (snapshot dates, query row counts, errors). The "why this report said what it said" layer.
- `CHANGELOG.md` (root) — when business rules or queries change, that's where it's recorded.
