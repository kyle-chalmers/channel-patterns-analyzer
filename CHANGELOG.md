# Changelog

Material changes to `BUSINESS_RULES.md`, `sql/`, or analyzer behavior — anything that would change what a future weekly report looks like or how it should be read. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

One entry per change, dated. Brief is fine; the goal is auditability, not narrative.

---

## 2026-05-25

Phase 2 Plan 02-01 SQL correctness fixes (D-05). All three files pass `bq` dry-run validation against the live `youtube_analytics` dataset.

- `sql/02_top_full_length_videos.sql`: before — joined on `video_metadata`'s latest snapshot only, used single-quoted `CURRENT_DATE('America/Phoenix')` in the `DATE_DIFF`, capped output at `LIMIT 20`; after — joins on the LEAST common snapshot of `video_metadata` and `daily_video_stats` via a new `latest_common` CTE, uses double-quoted `CURRENT_DATE("America/Phoenix")` per the project's canonical form, no row limit, header rewritten to cite `CLAUDE.md § "Age control is non-negotiable"` and `BUSINESS_RULES.md § "Data health expectations"` by section title. Impact on recent reports: would have changed top-N membership on any day where the two source tables landed at different snapshots. The 2026-05-25 Phase 1 report was unaffected (both tables at the same snapshot that day), so no retroactive number change; the fix is preventative for future runs.
- `sql/03_age_controlled_performance.sql`: same three changes as sql/02 (latest_common CTE, double-quoted Phoenix tz on both `DATE_DIFF` calls, `LIMIT 20` removed). The 14-day age filter in the WHERE clause now fires off Phoenix-local dates explicitly. Before/after impact: the same out-of-sync-table row-drop risk existed here and is also closed; the age-filter behavior was already correct under the prior single-quoted Phoenix form, so the filter's boundary classification doesn't change with this commit (the canonical-form switch is for project-wide consistency, not a behavior fix on the filter itself).
- `sql/04_data_health_check.sql`: replaced four single-quoted `CURRENT_DATE('America/Phoenix')` calls with double-quoted `CURRENT_DATE("America/Phoenix")` for project-wide canonical form. Header rewritten: the broken `BUSINESS_RULES.md §5` reference (the section number does not exist) is now `BUSINESS_RULES.md § "Data health expectations"`, and the conditional "if your scheduling timezone differs" language is replaced with a statement that Phoenix is the canonical timezone. No `days_stale` number changes from this commit.

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
