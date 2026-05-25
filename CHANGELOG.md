# Changelog

Material changes to `BUSINESS_RULES.md`, `sql/`, or analyzer behavior — anything that would change what a future weekly report looks like or how it should be read. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

One entry per change, dated. Brief is fine; the goal is auditability, not narrative.

---

## 2026-05-25 — Phase 1 first end-to-end run

- Ran /run-analyzer end-to-end against live BigQuery + live Notion. New child page created on the channel-patterns parent (https://www.notion.so/36bccd0549458105b8c4c3cc584e4d47). Local artifacts at reports/2026-05-25.md and runs/2026-05-25/.
- docs/runbook.md gained one new section: "Required environment variable is missing". Other runbook headings already matched the recipe's operator-message strings.
- Two recipe defects surfaced during the live run (logged in runs/2026-05-25/summary.json.warnings and in 01-04-SUMMARY.md for Phase 2 follow-up):
  - `bq query --max_rows=10000` is not a valid flag for the bq query subcommand (only `bq head` accepts it). Crashes with Python RecursionError in bq's flag-suggester.
  - Passing SQL as a positional argument fails when the SQL contains unicode box-drawing characters (`─` U+2500) used in this project's sql/ headers. Same RecursionError. Workaround: pipe SQL via stdin (`printf '%s' "$SQL" | bq --format=json query ...`).
- Phase 2c stale-data integration test did not apply this run: all four analytics tables snapshot 2026-05-25 (days_stale=0). The 89-day gap noted on 2026-05-24 for daily_video_analytics and daily_traffic_sources has resolved. Flagged for Phase 2 follow-up to design a synthetic stale-table simulation.

---

## 2026-05-25 — Phase 1 scaffold fixups

- Timezone: replaced bare `CURRENT_DATE()` with `CURRENT_DATE('America/Phoenix')` in sql/02, sql/03, sql/04. Aligns staleness and `days_since_published` with the rule in BUSINESS_RULES.md §3.
- Runbook: corrected `BUSINESS_RULES.md §5`→§3 and `§6`→§4 cross-references in docs/runbook.md.
- CONTEXT alignment: 01-CONTEXT.md prose updated from NOTION_PAGE_ID to NOTION_REPORT_PAGE_ID to match shipped .env.example and docs/runbook.md.

---

## 2026-05-24

- **Added persistent structure.** New top-level folders `reports/`, `runs/`, `docs/`, plus this `CHANGELOG.md`. Reports and per-run audit artifacts are now committed to git. `CLAUDE.md` updated to require writing to these folders each run and reading recent `reports/` to calibrate confidence. No change to BigQuery queries or business rules.
