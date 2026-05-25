# Changelog

Material changes to `BUSINESS_RULES.md`, `sql/`, or analyzer behavior — anything that would change what a future weekly report looks like or how it should be read. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

One entry per change, dated. Brief is fine; the goal is auditability, not narrative.

---

## 2026-05-25 — Phase 1 scaffold fixups

- Timezone: replaced bare `CURRENT_DATE()` with `CURRENT_DATE('America/Phoenix')` in sql/02, sql/03, sql/04. Aligns staleness and `days_since_published` with the rule in BUSINESS_RULES.md §3.
- Runbook: corrected `BUSINESS_RULES.md §5`→§3 and `§6`→§4 cross-references in docs/runbook.md.
- CONTEXT alignment: 01-CONTEXT.md prose updated from NOTION_PAGE_ID to NOTION_REPORT_PAGE_ID to match shipped .env.example and docs/runbook.md.

---

## 2026-05-24

- **Added persistent structure.** New top-level folders `reports/`, `runs/`, `docs/`, plus this `CHANGELOG.md`. Reports and per-run audit artifacts are now committed to git. `CLAUDE.md` updated to require writing to these folders each run and reading recent `reports/` to calibrate confidence. No change to BigQuery queries or business rules.
