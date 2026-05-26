---
status: partial
phase: 02-honest-analyst-depth
source: [VERIFICATION.md]
started: 2026-05-25T23:55:00-07:00
updated: 2026-05-25T23:55:00-07:00
---

## Current Test

[awaiting human testing]

## Tests

### 1. End-to-end /run-analyzer live run against BigQuery + Notion

expected: (a) New Notion child page renders with all six section headings in order: Data Health, Headline, What is working, What is not working, Patterns worth watching, Open questions. (b) Every pattern claim in the prose ends with `(label, n=N)` or appears in a table with Confidence + n columns. (c) `reports/{run_date}.md` matches the Notion page. (d) `runs/{run_date}/summary.json` contains both `prior_reports_consulted` (array of YYYY-MM-DD strings or `[]`) and `voice_audit` (with `checks_passed` listing canonical identifiers and `fixes_applied` as `{section, fix}` array). (e) `grep -nE '—|–' reports/{run_date}.md` returns zero matches. (f) `grep -niE '\b(leverage|robust|seamless|delve|navigate|transformative)\b' reports/{run_date}.md` returns zero matches. (g) First-person plural ("we", "us", "our") appears in at least the Headline or one finding section.
result: [pending]

### 2. SIMULATE_STALE live run to exercise D-12 disclaimer machinery

expected: `SIMULATE_STALE='daily_video_analytics:89,daily_traffic_sources:89' /run-analyzer` produces `reports/{run_date}.md` with one collapsed disclaimer per stale table per dependent section, naming the table and staleness in days, pointing to Data Health. `summary.json.warnings` contains `simulate_stale_applied: ...`. Phase 1's 89-day stale state resolved on 2026-05-25, so this is the only path to exercise the rule.
result: [pending]

### 3. Confirm `(label, n=N)` parentheticals survive the Notion render path

expected: Published Notion page shows `(moderate confidence, n=7)` (or whichever exact parenthetical the run produced) as plain text in the relevant paragraph — not auto-formatted as a Notion link/mention/inline-code and not stripped. Resolves PHASE1-ASSUMPTIONS-VERIFIED.md A5 (`not-yet-shipped`).
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
