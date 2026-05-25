---
phase: 01-first-notion-report-end-to-end
plan: 04
subsystem: runbook + recipe alignment
tags: [runbook, recipe, error-handling, phase-1-gate]
status: partial (Task 1 complete; Task 2 deferred to orchestrator)
requires:
  - .planning/phases/01-first-notion-report-end-to-end/01-04-PLAN.md
  - .claude/commands/run-analyzer.md (operator-message section names — contract)
  - .claude/skills/write-notion-report/SKILL.md (error categories)
provides:
  - docs/runbook.md § "Required environment variable is missing" (new section, covers env_missing category)
  - CHANGELOG.md entry placeholder for Phase 1 first end-to-end run
affects:
  - docs/runbook.md
  - CHANGELOG.md
tech-stack:
  added: []
  patterns:
    - "Recipe-as-contract: operator-message section names in /run-analyzer drive runbook headings, not the reverse."
key-files:
  created: []
  modified:
    - docs/runbook.md
    - CHANGELOG.md
decisions:
  - "Recipe is the contract; runbook follows. Plan 01-04 Task 1 confirmed all three section names cited by .claude/commands/run-analyzer.md ('BigQuery auth failure', 'Required table is missing or empty', 'Notion write failed') already exist in docs/runbook.md verbatim — no rename needed."
  - "Added exactly one new section ('Required environment variable is missing') for the env_missing preflight category. Deferred sections for skill_unavailable, report_dict_invalid, and no_bigquery_transport to Phase 3 (ERR-01), matching Plan 01-04's stated scope boundary."
  - "CHANGELOG entry uses a {run_date} placeholder so the orchestrator can substitute the real Phoenix-time date after Task 2 runs live."
metrics:
  duration: "~10 minutes"
  completed: "2026-05-25"
---

# Phase 01 Plan 04: First Notion Report End-to-End — Task 1 Summary

Aligned `docs/runbook.md` with the `/run-analyzer` recipe's operator-message strings and seeded a Phase-1 milestone entry in `CHANGELOG.md`. Task 2 (live end-to-end run) is deferred to the orchestrator because the worktree session has no live BigQuery or Notion MCPs.

## What Was Done

### Runbook alignment

Verified the three section names cited by `.claude/commands/run-analyzer.md`'s Step 8 operator-message templates already exist verbatim in `docs/runbook.md`:

| Recipe quote                                                       | Runbook heading                              | Status   |
| ------------------------------------------------------------------ | -------------------------------------------- | -------- |
| `docs/runbook.md § 'Notion write failed'`                          | `## Notion write failed`                     | matches  |
| `docs/runbook.md section "BigQuery auth failure"`                  | `## BigQuery auth failure`                   | matches  |
| `docs/runbook.md section "Required table is missing or empty"`     | `## Required table is missing or empty`      | matches  |
| `docs/runbook.md section "A required table is stale"` (BQ-FAIL)    | `## A required table is stale`               | matches  |

No renames needed. Added one new section: `## Required environment variable is missing`, inserted between `## Notion write failed` and `## Report says something the operator believes is wrong`. The section covers the recipe's Step 0 preflight failure (`category: "env_missing"` in `summary.json.errors[]`) and gives per-variable recovery steps for `NOTION_REPORT_PAGE_ID`, `BQ_PROJECT`, and `BQ_DATASET`.

Skipped (intentional, per plan scope): `skill_unavailable`, `report_dict_invalid`, `no_bigquery_transport` categories. Phase 3 (ERR-01) owns exhaustive runbook coverage; Phase 1 closes the loop only on what the recipe's three operator-message templates actually surface.

Checked the `## A required table is stale` body: cross-reference reads `BUSINESS_RULES.md §3`, already correct (Plan 01 fix carried). No §5/§6 references remain anywhere in the file.

### CHANGELOG entry

Prepended a dated entry above the existing `## 2026-05-25 — Phase 1 scaffold fixups` entry. The date is a placeholder string `{run_date — populated by orchestrator after live run}` so the orchestrator can substitute the real Phoenix-time date after Task 2 runs.

## Verification

All six acceptance criteria from `01-04-PLAN.md` Task 1 pass:

```
Check 1: every runbook section the recipe cites exists in docs/runbook.md
  OK: BigQuery auth failure
  OK: Required table is missing or empty
  OK: Notion write failed
Check 2: env-var-missing section added
  OK
Check 3: no remaining §5 or §6 cross-references
  OK
Check 4: CHANGELOG has the Phase-1-end-to-end entry
  OK
```

## Deviations from Plan

None. Task 1 executed exactly as written.

## Deferred Work

**Task 2 (checkpoint:human-verify, gate=blocking) is deferred to the orchestrator.** The executor running this plan operates inside a git worktree session that does not have live BigQuery (`bq` CLI / BQ MCP) or Notion MCP connectors loaded. Task 2 requires:

- A fresh `gcloud auth login` and a live `bq query` smoke test.
- The `write-notion-report` Skill loaded with `mcp__claude_ai_Notion__notion-*` tools.
- A populated `.env` with real `NOTION_REPORT_PAGE_ID`.
- The operator visually verifying the published Notion child page.

None of those are available in the executor's session. The orchestrator (operator session) will run `/run-analyzer` end-to-end inline after this work merges, fill the `{run_date}` placeholder in `CHANGELOG.md` with the real Phoenix-time date, paste the operator-message lines and `summary.json` excerpts into the SUMMARY, and resolve the five Phase-1 ROADMAP success criteria.

See `.planning/phases/01-first-notion-report-end-to-end/01-04-PLAN.md` Task 2 for the full operator script (Phase 2a happy-path, 2b forced-failure for ERR-02/PERSIST-03, 2c stale-data integration test).

## Known Stubs

- `CHANGELOG.md` entry contains the literal string `{run_date — populated by orchestrator after live run}`. The orchestrator MUST replace this with the actual Phoenix-time date of the live `/run-analyzer` run before merging Phase 1. This is intentional, not an oversight: the executor cannot know the date the operator will run the recipe.
- The CHANGELOG entry's third bullet ("Any new failure modes encountered during the live run are added below; if no new modes surfaced, this entry says so explicitly.") is a TODO for the orchestrator to resolve after Task 2. If Task 2 surfaces no new failure modes, replace the bullet with an explicit "No new failure modes surfaced." sentence.

## Threat Flags

None. Task 1 only edited markdown documentation; no new network endpoints, auth paths, file access patterns, or schema changes were introduced.

## Commits

- `c557d31` — `docs(01-04): align runbook section names with recipe operator messages` — `docs/runbook.md`, `CHANGELOG.md`

## Self-Check: PASSED

- `docs/runbook.md` contains `## Required environment variable is missing` — FOUND
- `CHANGELOG.md` contains `Phase 1 first end-to-end run` — FOUND
- Commit `c557d31` exists in `git log` — FOUND
- No §5/§6 cross-references remain in `docs/runbook.md` — confirmed
- All four recipe-cited runbook section headings present verbatim — confirmed
