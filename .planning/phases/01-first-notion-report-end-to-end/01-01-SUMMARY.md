---
phase: 01-first-notion-report-end-to-end
plan: 01
subsystem: scaffold-fixups
tags: [bigquery, notion, gitignore, mcp-probe, env-vars]
requires: []
provides:
  - sql-timezone-correct
  - runbook-section-refs-correct
  - env-var-name-aligned
  - skill-commit-pattern-ready
  - summary-json-schema-extended
  - mcp-probe-scaffold
affects:
  - sql/02_top_full_length_videos.sql
  - sql/03_age_controlled_performance.sql
  - sql/04_data_health_check.sql
  - docs/runbook.md
  - .planning/phases/01-first-notion-report-end-to-end/01-CONTEXT.md
  - CHANGELOG.md
  - .gitignore
  - runs/README.md
  - .planning/phases/01-first-notion-report-end-to-end/01-01-PROBE-NOTES.md
tech_stack_added: []
patterns_used:
  - dual-negation gitignore (corrected: `dir/*` not `dir/`)
  - America/Phoenix timezone anchor for BigQuery date math
key_files_created:
  - .planning/phases/01-first-notion-report-end-to-end/01-01-PROBE-NOTES.md
key_files_modified:
  - sql/02_top_full_length_videos.sql
  - sql/03_age_controlled_performance.sql
  - sql/04_data_health_check.sql
  - docs/runbook.md
  - .planning/phases/01-first-notion-report-end-to-end/01-CONTEXT.md
  - CHANGELOG.md
  - .gitignore
  - runs/README.md
decisions:
  - Corrected gitignore broad pattern from `.claude/skills/` to `.claude/skills/*` so the negation re-includes actually apply (the trailing-slash form short-circuits git's directory traversal, and the negations are silently no-ops).
  - Kept the env-var name `NOTION_REPORT_PAGE_ID` (per RESEARCH §10 Q1); aligned CONTEXT.md prose accordingly.
metrics:
  duration_seconds: 179
  tasks_completed: 3
  tasks_total: 3
  completed_date: 2026-05-25
---

# Phase 1 Plan 1: Phase 1 scaffold fixups Summary

Reconciled the env-var name across the Phase 1 surface, fixed three scaffold defects that would otherwise corrupt downstream outcomes (UTC timezone in date math, broken `BUSINESS_RULES.md §5/§6` cross-references, hostile gitignore for the Skill that Plan 02 ships), extended `runs/README.md` for two additive `summary.json` fields, and scaffolded the MCP-probe notes Plans 02 and 03 read before generating tool invocations. The probe block remains a checkpoint until an operator with the BigQuery + Notion MCPs attached fills in the live outputs.

## Tasks Completed

| Task | Name | Commit |
|------|------|--------|
| 1 | Fix CURRENT_DATE timezone, BUSINESS_RULES section refs, and env-var name | 8874303 |
| 2 | Update .gitignore to commit the write-notion-report Skill and extend runs/README.md schema | fdead0c |
| 3 | Probe BigQuery MCP and Notion MCP argument shapes; record findings (SCAFFOLD ONLY — see "Checkpoint open" below) | 4041064 |

## Files Created

- `.planning/phases/01-first-notion-report-end-to-end/01-01-PROBE-NOTES.md` — Wave-0 probe template; references both `execute_sql_readonly` and `notion-fetch`; placeholder paste blocks are unfilled (see Checkpoint open).

## Files Modified

- `sql/02_top_full_length_videos.sql` — line 20: `CURRENT_DATE()` → `CURRENT_DATE('America/Phoenix')` for the `days_since_published` calculation.
- `sql/03_age_controlled_performance.sql` — two occurrences (lines 24 and 35): same timezone fix for the age window.
- `sql/04_data_health_check.sql` — four occurrences (one per UNION ALL block): same timezone fix for `days_stale`.
- `docs/runbook.md` — three cross-references corrected: `BUSINESS_RULES.md §5` → §3 (line 31, "A required table is stale" section); `§6` → §4 (lines 47, 57, 58, "Required table is missing or empty" and "BigQuery schema drift" sections).
- `.planning/phases/01-first-notion-report-end-to-end/01-CONTEXT.md` — two occurrences of `NOTION_PAGE_ID` renamed to `NOTION_REPORT_PAGE_ID` (D-06 prose and `<canonical_refs>` block) per RESEARCH §10 Q1 recommendation; the shipped `.env.example` and `docs/runbook.md` already use the longer name.
- `CHANGELOG.md` — single dated entry `## 2026-05-25 — Phase 1 scaffold fixups` covering all three Task 1 changes; original 2026-05-24 entry preserved below.
- `.gitignore` — broad-skill ignore line changed from `.claude/skills/` to `.claude/skills/*`, then two negation lines added re-including `.claude/skills/write-notion-report/` and `.claude/skills/write-notion-report/**`. See "Deviations from plan" below for why the original literal pattern would not have worked.
- `runs/README.md` — JSON schema block gains `transport` (`"bq_cli"`) and `notion_url` fields; explanatory prose added one paragraph below documenting both.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] gitignore dual-negation pattern as written in the plan did not actually un-ignore the Skill.**

- **Found during:** Task 2 verification (Check 2).
- **Issue:** The plan's literal instruction was to leave `.gitignore` line 39 (`.claude/skills/`) unchanged and add `!.claude/skills/write-notion-report/` + `!.claude/skills/write-notion-report/**` after it. Verified empirically that this pattern leaves `git check-ignore -v .claude/skills/write-notion-report/SKILL.md` still matching the broad ignore (exit 0 — file ignored). Reproduced in a clean `/tmp/gitest` with the same three-line `.gitignore` and got the same result. Per git's documented gitignore semantics ("It is not possible to re-include a file if a parent directory of that file is excluded"), a trailing-slash directory ignore short-circuits git's traversal into the directory and the negations underneath are silently no-ops. The plan's RESEARCH §8 documents the dual-negation pattern as the fix, but the fix only works when the broad ignore does not match the directory itself.
- **Fix:** Changed the broad ignore from `.claude/skills/` to `.claude/skills/*` (matches contents but does not bar traversal), then kept the two negation lines exactly as written. Verified: `git check-ignore` returns exit 1 for `.claude/skills/write-notion-report/SKILL.md` and exit 0 for `.claude/skills/some-other-skill/SKILL.md` — both branches behave as required by Task 2's acceptance criteria checks 2 and 3.
- **Files modified:** `.gitignore` (with an inline comment explaining the trailing-slash gotcha so the next operator does not re-introduce it).
- **Commit:** `fdead0c`.

Plan acceptance-criteria note: the plan's literal check 5 ("the pre-existing `.gitignore` line `.claude/skills/` is still present") is no longer satisfied byte-for-byte because the line now reads `.claude/skills/*`. The substantive intent — broad ignore of `.claude/skills/` contents preceding the negation — is preserved. The functional acceptance criteria (checks 2 and 3 — file ignored vs not) pass cleanly.

### Architectural Changes

None.

## Auth Gates Encountered

None during Tasks 1 and 2. Task 3's probes are blocked on MCP-tool availability (not auth) — see Checkpoint open.

## Checkpoint Open (Task 3 — `human-verify`, gate=blocking)

The Plan 01-01 executor's session had only the Microsoft Learn and Zapier MCPs attached, not `mcp__claude_ai_Google_Cloud_BigQuery__*` or `mcp__claude_ai_Notion__*`. The two live probes (BigQuery `execute_sql_readonly` argument shape and Notion `notion-fetch` against `NOTION_REPORT_PAGE_ID`) could not be performed during automated execution. The probe-notes file was scaffolded with placeholder paste blocks and committed (`4041064`) so the file exists and references both `execute_sql_readonly` and `notion-fetch`, but the paste blocks remain unfilled.

**Operator action required before Plans 02/03 begin:**

1. Open a Claude Code session with both `mcp__claude_ai_Google_Cloud_BigQuery__*` and `mcp__claude_ai_Notion__*` MCPs attached.
2. Confirm `.env` has `NOTION_REPORT_PAGE_ID` set to the real channel-patterns parent page UUID.
3. Run the BigQuery probe: invoke `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly` with the test query `SELECT 1 AS one, 'hello' AS label`. Paste the raw response and the actual argument-key names into the BigQuery block in `01-01-PROBE-NOTES.md`.
4. Run the Notion probe: invoke `mcp__claude_ai_Notion__notion-fetch` against the `NOTION_REPORT_PAGE_ID` value (try both dashed and undashed UUID forms; record what each returns). Paste the page metadata (not the body, not the env value itself) into the Notion block.
5. Reply "approved" once both blocks have real outputs.

This deferred completion does not affect Plan 01-01's other Phase-1-scope fixes; SQL, runbook, env-var, gitignore, and summary-schema work all landed.

## Known Stubs

The Task-3 probe-notes file contains intentional placeholder blocks (`<paste raw MCP response here, …>`) that will only be filled when an MCP-enabled session runs the live probes. These are documented in the file itself with an explicit "Operator action required" header and in this Summary above. Plans 02 and 03 are designed to halt at their first MCP-invocation step if these blocks remain unfilled (per the file's "What Plans 02 and 03 read from this file" section).

## Threat Flags

None. The committed files contain no environment-variable values, no UUIDs, no project IDs; the probe-notes file explicitly forbids recording them per T-01-01 disposition.

## Self-Check: PASSED

- `sql/02_top_full_length_videos.sql` — FOUND, contains `CURRENT_DATE('America/Phoenix')`.
- `sql/03_age_controlled_performance.sql` — FOUND, contains `CURRENT_DATE('America/Phoenix')` (2 occurrences).
- `sql/04_data_health_check.sql` — FOUND, contains `CURRENT_DATE('America/Phoenix')` (4 occurrences).
- `docs/runbook.md` — FOUND, no `BUSINESS_RULES.md §5` or `§6` reference remains.
- `.planning/phases/01-first-notion-report-end-to-end/01-CONTEXT.md` — FOUND, no `NOTION_PAGE_ID` reference remains.
- `CHANGELOG.md` — FOUND, contains `2026-05-25 — Phase 1 scaffold fixups` heading.
- `.gitignore` — FOUND, `.claude/skills/*` broad ignore present, two negation lines present.
- `runs/README.md` — FOUND, contains `"transport":` and `"notion_url":`.
- `.planning/phases/01-first-notion-report-end-to-end/01-01-PROBE-NOTES.md` — FOUND, contains `execute_sql_readonly` and `notion-fetch`.
- Commits: `8874303`, `fdead0c`, `4041064` — all FOUND via `git log --oneline`.
