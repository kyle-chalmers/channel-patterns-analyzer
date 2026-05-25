---
phase: 01-first-notion-report-end-to-end
plan: 04
subsystem: runbook + recipe alignment
tags: [runbook, recipe, error-handling, phase-1-gate]
status: complete (Task 1 by executor; Task 2 by orchestrator inline)
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

## Task 2 (orchestrator inline)

The orchestrator ran `/run-analyzer` end-to-end on 2026-05-25 with all MCPs attached. All five Phase-1 ROADMAP success criteria pass.

### Phase 2a happy-path

Operator message: `Run 2026-05-25 complete. Notion: https://www.notion.so/36bccd0549458105b8c4c3cc584e4d47. Local: reports/2026-05-25.md`

Artifacts:
- `reports/2026-05-25.md` (1742 bytes, all six sections present)
- `runs/2026-05-25/report.md` (mirror)
- `runs/2026-05-25/summary.json` (notion_write_ok=true, 4 snapshot_dates, 0 stale_tables, transport=bq_cli)
- `runs/2026-05-25/queries/data_health.json` (4 rows)
- `runs/2026-05-25/queries/top_full_length_videos.json` (20 rows)

Notion child page rendered with `Weekly report, 2026-05-25` title, Data Health section first, all six report sections present (none silently omitted), `What is working` names "Claude Code vs Manual Jira Ticket Work" (10,271 views, 199 days) with confidence label "low".

### Phase 2b forced-failure (PERSIST-03 + ERR-02 verification)

Commented out `NOTION_REPORT_PAGE_ID` in `.env`, ran a synthetic-suffix run under `run_date=2026-05-25-failtest` to keep happy-path artifacts intact.

Operator message: `Run 2026-05-25-failtest FAILED at preflight: NOTION_REPORT_PAGE_ID not set. Recovery: see docs/runbook.md § 'Required environment variable is missing'.`

Verified:
- `runs/2026-05-25-failtest/summary.json` exists with `errors[0] = {"category": "env_missing", "message": "NOTION_REPORT_PAGE_ID not set", "step": "preflight"}`.
- `reports/2026-05-25-failtest.md` NOT written (Step-0 preflight stop, as designed).
- `notion_write_ok: false`.

Restored `.env` after the test.

### Phase 2c stale-data integration test

Did NOT apply this run. All four analytics tables snapshot 2026-05-25 (days_stale=0). The 89-day gap noted in STATE.md on 2026-05-24 for `daily_video_analytics` and `daily_traffic_sources` has resolved. Flagged below for Phase 2 follow-up.

### Five ROADMAP Phase-1 success criteria

1. New child page appeared under channel-patterns within 60 seconds: **YES**.
2. Page leads with Data Health section naming snapshot_date per table and flagging stale tables: **YES** (no stale tables this run; Data Health prose explicitly states the 3-day freshness contract is met).
3. `runs/{run_date}/queries/*.json` and `runs/{run_date}/summary.json` written per `runs/README.md` schema: **YES**.
4. Forced-failure run produced `summary.json` with `errors[]` populated; operator saw a runbook-pointed message: **YES**.
5. Reading `.claude/skills/write-notion-report/SKILL.md` frontmatter in isolation, the trigger was unambiguous: **YES** (Skill auto-loaded mid-session after Plan 02 merge; description + when_to_use sufficient to invoke).

## Recipe defects surfaced (Phase 2 backlog)

1. **`bq query --max_rows=10000` is invalid.** The `--max_rows` flag belongs to `bq head`, not `bq query`. The recipe's mandatory inclusion crashes bq with a Python RecursionError in the flag-suggester. Fix in Phase 2: drop the flag (default 100-row cap is fine for Phase 1 queries; Phase 2 queries needing more should use `LIMIT` in SQL or split into multiple queries). If a row-count override is genuinely needed for `bq query`, the right flag is `--n` (short for `--n_rows`), not `--max_rows`.
2. **Positional SQL fails on unicode box-drawing chars.** bq's flag parser treats lines starting with `─` (U+2500) as flag-like input and crashes. This project's sql/ files use box-drawing characters in section headers (e.g., `-- ─── Data health check ───────────────────────────────────────`). Fix in Phase 2: change the recipe's invocation form from `bq ... "$SQL"` to `printf '%s' "$SQL" | bq ...` (stdin pipe). The MCP transport (`bq_mcp`) is unaffected because SQL is passed as a JSON argument.
3. **Phase 2c (stale-data integration test) needs a synthetic fixture.** The current Phase 2c design relied on the live stale-table state from 2026-05-24, which has since resolved. Fix in Phase 2: design a forced-stale-table simulation (e.g., a query that aliases a stale snapshot or a config flag that injects synthetic stale rows for testing).

## Commits

- `c557d31` — `docs(01-04): align runbook section names with recipe operator messages` — `docs/runbook.md`, `CHANGELOG.md` (Task 1, executor)
- `77aa260` — `docs(01-04): add SUMMARY.md for plan 01-04 Task 1` (Task 1 closer, executor)
- (this commit) — Task 2 live-run artifacts + CHANGELOG date substitution + SUMMARY extension (orchestrator inline)

## Self-Check: PASSED

- `docs/runbook.md` contains `## Required environment variable is missing` — FOUND
- `CHANGELOG.md` contains `Phase 1 first end-to-end run` — FOUND
- Commit `c557d31` exists in `git log` — FOUND
- No §5/§6 cross-references remain in `docs/runbook.md` — confirmed
- All four recipe-cited runbook section headings present verbatim — confirmed
