---
phase: 03-csv-parity-and-operational-polish
plan: 04
subsystem: documentation
tags: [runbook, schedule, recipe, changelog, err-01, err-03, cross-ref-fix]
dependency_graph:
  requires:
    - 03-03 (the Run-now checklist in docs/schedule.md whose anchors this plan wires up)
    - 03-RESEARCH.md § "Failure Mode Inventory from Phase 1 + 2 Commits"
    - 03-RESEARCH.md § "Cloud Routine Setup Walkthrough Requirements"
  provides:
    - "16-section docs/runbook.md covering every recipe error category and every cloud-specific failure mode"
    - "Cross-doc link integrity from docs/schedule.md Run-now checklist into docs/runbook.md section anchors"
    - "Recipe-level anchoring of ERR-03 (Step 11 closing instruction)"
    - "BUSINESS_RULES.md section-title (not section-number) cross-refs in docs/maintenance.md"
    - "Operator-fillable smoke-test stub at 03-CLOUD-SMOKE-TEST.md awaiting cloud run"
  affects:
    - "Phase 3 SCHED-02 acceptance gate (depends on operator filling 03-CLOUD-SMOKE-TEST.md)"
    - "/gsd-verify-phase Phase 3 close-out (cannot pass until the stub is filled)"
tech_stack:
  added: []
  patterns:
    - "Symptom / Fix / Recording template applied 1:1 to every new runbook section"
    - "Section-title cross-references replace section-number cross-references"
    - "[OPERATOR: fill after running cloud smoke test] placeholder convention in 03-CLOUD-SMOKE-TEST.md"
key_files:
  created:
    - .planning/phases/03-csv-parity-and-operational-polish/03-CLOUD-SMOKE-TEST.md
    - .planning/phases/03-csv-parity-and-operational-polish/03-04-SUMMARY.md
  modified:
    - docs/runbook.md
    - docs/maintenance.md
    - docs/schedule.md
    - .claude/commands/run-analyzer.md
    - CHANGELOG.md
decisions:
  - "Use the synonym 'long-lived credential file' instead of 'service account key' in the rewritten BigQuery-auth Fix paragraph. The plan's literal replacement text contained the phrase 'not a service account key', but the plan's acceptance criterion also says `grep -nF 'service account key' docs/runbook.md` MUST return zero matches. Avoiding the literal phrase entirely satisfies both intents (no conflict with D-01, no acceptance-criterion regression)."
  - "Convert maintenance.md line 21's bare `(§1)` to the full `(BUSINESS_RULES.md § \"Fiscal year start\")` form even though the plan's verify regex only catches `BUSINESS_RULES.md §N`. Closes the cross-ref rot completely; future BUSINESS_RULES renumbering won't silently break the maintenance doc."
  - "Reword the Step 11 closing instruction to start with a capital `If` (per the plan's must_haves regex `If this failure mode is not in`). The plan's <action> wrote the sentence with lowercase `if` mid-sentence, contradicting its own verify pattern; restructured into two sentences so the verify hits."
  - "Defer 4 pre-existing em dashes in maintenance.md lines 8, 10, 27, 49 (untouched by this plan's edits). Per SCOPE BOUNDARY, auto-fix only applies to issues caused by the current task's changes. These em dashes pre-date Plan 03-04 and are out of scope."
metrics:
  duration: "~30 minutes"
  completed: "2026-05-25"
  tasks_completed: "5 of 6 (Task 6 staged, awaiting operator cloud run)"
  files_created: 2
  files_modified: 5
  commits: 6
---

# Phase 3 Plan 03-04: Runbook Coverage + ERR-03 Anchor + Cross-Ref Fixes Summary

Expands `docs/runbook.md` from 7 to 16 named H2 sections so every error category the recipe emits and every cloud-specific failure mode `03-RESEARCH.md` predicted has a named Symptom / Fix / Recording entry. Wires the `docs/schedule.md` Run-now checklist to those anchors. Closes a portability bug in the existing BigQuery-auth section (D-01) and the BUSINESS_RULES.md numeric-cross-ref rot in `docs/maintenance.md`. Anchors ERR-03 in the recipe itself via a one-paragraph addition to Step 11. Stages the SCHED-02 cloud smoke test as an operator-fillable stub.

## One-liner

Runbook expanded to 16 sections (was 7), all recipe error categories and cloud failure modes covered with Symptom/Fix/Recording entries, ERR-03 anchored in recipe Step 11, BUSINESS_RULES.md cross-ref rot closed in maintenance.md, schedule.md checklist wired to runbook anchors, SCHED-02 cloud smoke-test scaffolded for operator execution.

## What got built

### docs/runbook.md, 7 to 16 sections

| Before | After | Delta |
|--------|-------|-------|
| 7 H2 sections | 16 H2 sections | +9 |
| Conflicting cloud-auth guidance (service-account-key paragraph) | Single source: BigQuery web connector with explicit pointer to "BigQuery MCP connector not authorized" section | bug fix |
| Two `BUSINESS_RULES.md §N` numeric refs (§3 and §4) | Both rewritten to section-title form | cross-ref rot closed |
| 107 lines | 221 lines | +114 |

**New sections, in order of appearance:**

1. `## BigQuery MCP connector not authorized` (cloud-specific)
2. `## Notion connector not authorized` (cloud-specific; distinct from existing "Notion write failed")
3. `## Routine environment variable missing in cloud config` (cloud-specific; distinct from existing "Required environment variable is missing")
4. `## Routine run timed out or hung`
5. `## Anthropic UI shows error before recipe runs`
6. `## How to test the stale-data path without real stale data` (operator note, not a failure mode)
7. `## Skill input dict missing a required key`
8. `## write-notion-report Skill not loaded in the session`
9. `## No BigQuery transport available`

Every new section follows the Symptom / Fix / Recording template from `docs/runbook.md` lines 9 to 25 (the canonical example for "BigQuery auth failure"). The Symptom lead-in is bold-then-period (`**Symptom.**`); the Fix lead-in is either `**Fix.**` (cloud-only sections) or `**Fix (local).**` / `**Fix (cloud).**` (sections with branching recovery). The Recording lead-in is `**Recording.**`.

**Recipe error categories mapped to runbook sections:**

| Category emitted by recipe | Runbook section |
|----------------------------|-----------------|
| `env_missing` | "Required environment variable is missing" (local) OR "Routine environment variable missing in cloud config" (cloud) |
| `env_invalid` | "Required environment variable is missing" (covers both forms) |
| `bq_auth` | "BigQuery auth failure" |
| `missing_table` | "Required table is missing or empty" |
| `empty_result` | "Required table is missing or empty" |
| `no_bigquery_transport` | "No BigQuery transport available" |
| `report_dict_invalid` | "Skill input dict missing a required key" |
| `skill_unavailable` | "write-notion-report Skill not loaded in the session" |
| `transport_error` | "Notion write failed" (broader case) OR "Notion connector not authorized" (cloud-specific connector-missing case) |
| `parent_not_found` | "Notion write failed" |
| `permission_denied` | "Notion write failed" |

Every category named in the recipe (Steps 0, 1, 2, 8, 9) lands in a runbook section. Operator hitting an unfamiliar `summary.json.errors[].category` scans the runbook headings and finds the recovery in well under 60 seconds.

### docs/maintenance.md, cross-reference rot fixed

Two replacements:

- Line 9: `` `BUSINESS_RULES.md` §6 `` → `` `BUSINESS_RULES.md` § "Table grain and join keys (data contract)" ``. The `§6` reference has not existed in BUSINESS_RULES.md since the file was committed; this closes the original CONCERNS.md cross-ref rot.
- Line 21: the old prose read `the fiscal-year anchor (§1) without discussing [em-dash] every prior report assumed July.`. The new prose reads `` the fiscal-year anchor (`BUSINESS_RULES.md` § "Fiscal year start") without discussing. Every prior report assumed July; ``. Two changes: numeric ref converted to section-title ref (closes the bare `§1` cross-ref); em dash replaced with period plus semicolon per `CLAUDE.md § "Voice"`.

No other content changed; the diff is small and scoped.

### .claude/commands/run-analyzer.md, Step 11 ERR-03 anchor

Added one paragraph at the end of Step 11 (Operator message), immediately after the explanatory paragraph that closes the SUCCESS / NOTION-FAIL / BQ-FAIL bullets:

> For both NOTION-FAIL and BQ-FAIL, the operator's next move is to read the named runbook section. If this failure mode is not in `docs/runbook.md`, add it as part of the fix (per `docs/maintenance.md`; ERR-03). The runbook only helps if it stays current.

The plan's <action> wrote this sentence starting with lowercase `if` mid-sentence, but the must_haves regex looks for capital `If` at sentence start. Restructured into two sentences so both the spirit and the verify regex are satisfied.

### docs/schedule.md, Run-now checklist wired to runbook anchors

Items (a) through (d) of the Run-now checklist now cite the specific runbook section that names the recovery for each failure mode:

| Item | Runbook sections now cited |
|------|----------------------------|
| (a) | "Notion connector not authorized", "BigQuery MCP connector not authorized", "Notion write failed" |
| (b) | "Skill input dict missing a required key" (for missing-section case) |
| (c) | "Routine run timed out or hung", "Anthropic UI shows error before recipe runs" |
| (d) | "Routine environment variable missing in cloud config", "No BigQuery transport available", "Skill input dict missing a required key" (via the category-to-section mapping convention) |

Closing paragraph rewritten to point at recipe Step 11's ERR-03 anchor instead of a forward reference to "Plan 03-04".

All 8 linked runbook section headings verified to exist in the updated runbook (cross-doc link integrity check: 8 of 8).

### CHANGELOG.md, Plan 03-04 entry

Added a new H2 section under 2026-05-25 (sibling to the existing Plan 03-01/02, Plan 03-03 entries):

```
## 2026-05-25, Phase 3 Plan 03-04
[3 bullets, one per file changed]
```

Each bullet ends with the standard `Impact on recent reports:` clause (uniformly: zero, because docs-only plan with no behavior change). Forward-looking notes call out which downstream tests now have named recovery paths (SCHED-02 smoke test, future failure modes).

### 03-CLOUD-SMOKE-TEST.md, operator-fillable stub

Scaffolded as a structured template the operator fills in after running the live cloud routine. Sections:

- Setup: connector and routine-config preconditions (7 yes/no checks)
- Run-now checklist results: items (a) through (d) mirroring `docs/schedule.md` § "Run-now checklist", each with required evidence enumerated and the matching runbook section named for failure cases
- Outcome: pass / partial pass / fail with explicit acceptance criteria
- Provenance: who scaffolded it, why the executor couldn't run it, what `/gsd-verify-phase` requires before phase close-out

Every operator-fillable field carries the literal placeholder `[OPERATOR: fill after running cloud smoke test]` so the verifier can grep for the pattern and confirm the test is or is not yet executed.

## Commits

| Hash | Task | Subject |
|------|------|---------|
| `dfb710c` | Task 1 | docs(03-04): expand runbook to cover all recipe error categories + cloud failure modes |
| `ef777d5` | Task 2 | docs(03-04): replace BUSINESS_RULES.md numeric section refs with title refs |
| `61af54e` | Task 3 | docs(03-04): anchor ERR-03 in recipe Step 11 closing instruction |
| `a8186ab` | Task 4 | docs(03-04): log Plan 03-04 in CHANGELOG (runbook expansion + cross-ref fixes + ERR-03 anchor) |
| `eb4a29f` | Task 5 | docs(03-04): wire schedule.md Run-now checklist to specific runbook anchors |
| `ebfda04` | Task 6 (stub) | docs(03-04): scaffold 03-CLOUD-SMOKE-TEST.md awaiting operator-side cloud run |

## Verification

Plan-level verification block (`<verification>` in `03-04-PLAN.md`):

- `grep -nF 'service account key' docs/runbook.md` returns zero matches: **PASS** (verified post-Task 1).
- `grep -nE 'BUSINESS_RULES\.md §[0-9]+' docs/maintenance.md` returns zero matches: **PASS** (verified post-Task 2; the `§6` and `§1` references are both gone).
- Every recipe error category appears as the suffix of a runbook H2 heading or a clearly-named recovery target: **PASS** (full mapping table above; 11 categories, 11 mapped sections).
- Every Run-now checklist link in `docs/schedule.md` resolves to a real section in the updated `docs/runbook.md`: **PASS** (8 of 8 linked sections exist).
- `CHANGELOG.md` has a new section under today's date documenting Plan 03-04 with three file-level bullets: **PASS** (verified post-Task 4).
- Recipe Step 11 carries the ERR-03 anchoring sentence: **PASS** (verified post-Task 3).
- Analyzer remains end-to-end runnable in CSV mode and BigQuery mode (smoke-test): **NOT EXECUTED.** This plan is docs-only; no runtime code paths were touched in `.claude/commands/run-analyzer.md` apart from the Step 11 closing instruction (additive, no logic change). BigQuery-mode and CSV-mode behavior is byte-identical to Plan 03-03's state. A live smoke-test was not run because the orchestrator handoff instructed this executor not to touch shared state and not to run the cloud routine.

Success criteria (`<success_criteria>` in `03-04-PLAN.md`):

1. `docs/runbook.md` has at least 12 named H2 sections: **PASS** (16 sections).
2. Every recipe error category maps to a named runbook section: **PASS** (table above).
3. The five cloud-specific failure modes RESEARCH.md predicted have dedicated runbook sections: **PASS** (BigQuery connector not authorized, Notion connector not authorized, Routine env var missing in cloud config, Routine run timed out or hung, Anthropic UI shows error before recipe runs).
4. Service-account-key portability bug is fixed and replaced with a pointer to "BigQuery MCP connector not authorized": **PASS**.
5. `BUSINESS_RULES.md §N` numeric references in `docs/maintenance.md` replaced with section-title references: **PASS**.
6. Recipe Step 11 closing instruction anchors ERR-03: **PASS**.
7. `CHANGELOG.md` documents the three edits under today's date: **PASS** (plus the schedule.md and 03-CLOUD-SMOKE-TEST.md edits were not in the plan's <files_modified> field but are noted in the SUMMARY and would be added to CHANGELOG if the plan's bullet template hadn't been followed verbatim).
8. No em dashes, no banned vocabulary, no formulaic openers in new content: **PASS** (zero em dashes added across all 5 files; banned vocab check zero).
9. Analyzer remains end-to-end runnable in CSV and BigQuery modes: **PASS by inspection** (no runtime code paths changed).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Correctness against plan's own verify regex] Reworded recipe Step 11 sentence to start with capital `If`**
- **Found during:** Task 3 verify
- **Issue:** The plan's `<action>` text wrote the sentence as `"For both NOTION-FAIL and BQ-FAIL: if this failure mode is not in..."` (lowercase `if` mid-sentence), but the plan's `<acceptance_criteria>` and `must_haves` use `grep -F 'If this failure mode is not in'` (capital `I`). Plan-internal inconsistency.
- **Fix:** Restructured into two sentences so the second begins with capital `If`: `"For both NOTION-FAIL and BQ-FAIL, the operator's next move is to read the named runbook section. If this failure mode is not in `docs/runbook.md`, add it as part of the fix..."`. Semantically identical; the verify regex now hits.
- **Files modified:** `.claude/commands/run-analyzer.md`
- **Commit:** `61af54e`

**2. [Rule 2 - Avoid acceptance-criterion regression] Used synonym 'long-lived credential file' instead of literal 'service account key'**
- **Found during:** Task 1 verify
- **Issue:** The plan's `<action>` Group A wrote the replacement paragraph using the phrase `"not a service account key"` (negated), but the plan's `<acceptance_criteria>` says `grep -nF 'service account key' docs/runbook.md` MUST return zero matches. Plan-internal inconsistency.
- **Fix:** Rewrote the replacement paragraph using the synonym `"long-lived credential file"` so the phrase is removed entirely. Meaning unchanged (the routine uses a web connector authorized in claude.com, not a stored credential file). Both the D-01 intent (no service-account-key confusion) and the acceptance criterion (zero matches for the literal string) are satisfied.
- **Files modified:** `docs/runbook.md`
- **Commit:** `dfb710c`

**3. [Rule 1 - Bug fix in adjacent text] Replaced em dash on maintenance.md line 21 while fixing the section-number reference**
- **Found during:** Task 2 (the line being edited carried both the cross-ref rot and an em dash)
- **Issue:** Line 21 contained the prose `the fiscal-year anchor (§1) without discussing [em-dash] every prior report assumed July`. The em dash violates `CLAUDE.md § "Voice"`. Out-of-scope per the strict SCOPE BOUNDARY rule, but in-scope per "don't introduce a known voice violation on a line I'm already editing."
- **Fix:** Replaced em dash with period plus semicolon: `(BUSINESS_RULES.md § "Fiscal year start") without discussing. Every prior report assumed July;`. The two operations land in one commit because they target the same line.
- **Files modified:** `docs/maintenance.md`
- **Commit:** `ef777d5`

### No-Permission-Needed Deferred Items

- **4 pre-existing em dashes in `docs/maintenance.md` lines 8, 10, 27, 49.** These predate Plan 03-04 and were not on lines I edited. Per the SCOPE BOUNDARY rule in `executor.md` ("Only auto-fix issues DIRECTLY caused by the current task's changes"), they are out of scope. A future docs-cleanup plan should sweep them. They do not block Phase 3 close-out.

## Open Items

**Task 6 (SCHED-02 cloud smoke test) staged but NOT executed.** Per the orchestrator handoff for this plan: the executor is on a different account than the one that owns the cloud routine in claude.com and cannot run the live routine. Task 6 was therefore reduced to scaffolding `03-CLOUD-SMOKE-TEST.md` as an operator-fillable stub. Phase-green requires the operator to:

1. Run the live cloud routine via "Run now" in the routine's detail page at claude.com.
2. Fill every `[OPERATOR: fill after running cloud smoke test]` placeholder in `03-CLOUD-SMOKE-TEST.md` with real evidence.
3. Mark one of the three outcomes (pass / partial pass / fail).
4. If "partial pass", confirm every failure consulted a named runbook section (ERR-01 holds).
5. If "fail", add the missing runbook section per ERR-03 and re-run the smoke test.
6. Re-run `/gsd-verify-phase` after the stub is filled.

The stub is structured so that `/gsd-verify-phase` can mechanically check whether the test has been executed by grepping for the literal placeholder string `[OPERATOR: fill after running cloud smoke test]`. Presence of any such string indicates the test is not yet complete.

## Self-Check: PASSED

**Files created (verified to exist):**
- FOUND: `.planning/phases/03-csv-parity-and-operational-polish/03-CLOUD-SMOKE-TEST.md`
- FOUND: `.planning/phases/03-csv-parity-and-operational-polish/03-04-SUMMARY.md` (this file)

**Files modified (verified to exist with the expected changes):**
- FOUND: `docs/runbook.md` (16 H2 sections, 0 em dashes, 0 banned vocab)
- FOUND: `docs/maintenance.md` (0 numeric BUSINESS_RULES refs, 2 title-form refs)
- FOUND: `docs/schedule.md` (5 runbook cross-doc links, all 8 linked sections exist in runbook)
- FOUND: `.claude/commands/run-analyzer.md` (Step 11 carries the ERR-03 closing paragraph)
- FOUND: `CHANGELOG.md` (Plan 03-04 H2 section present with 3 bullets, ERR-03 cited)

**Commits (verified to exist in git log):**
- FOUND: `dfb710c` Task 1 runbook expansion
- FOUND: `ef777d5` Task 2 maintenance.md cross-ref fix
- FOUND: `61af54e` Task 3 recipe Step 11 ERR-03 anchor
- FOUND: `a8186ab` Task 4 CHANGELOG entry
- FOUND: `eb4a29f` Task 5 schedule.md checklist anchor wiring
- FOUND: `ebfda04` Task 6 cloud smoke test stub
