# Changelog

Material changes to `BUSINESS_RULES.md`, `sql/`, or analyzer behavior — anything that would change what a future weekly report looks like or how it should be read. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

One entry per change, dated. Brief is fine; the goal is auditability, not narrative.

---

## 2026-05-24

- **Added persistent structure.** New top-level folders `reports/`, `runs/`, `docs/`, plus this `CHANGELOG.md`. Reports and per-run audit artifacts are now committed to git. `CLAUDE.md` updated to require writing to these folders each run and reading recent `reports/` to calibrate confidence. No change to BigQuery queries or business rules.
