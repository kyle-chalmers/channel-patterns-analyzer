---
phase: 01-first-notion-report-end-to-end
plan: 03
subsystem: analyzer-recipe
tags: [slash-command, recipe, bigquery, notion, persistence, error-handling]
requires:
  - sql-timezone-correct
  - skill-commit-pattern-ready
  - summary-json-schema-extended
  - mcp-probe-scaffold
provides:
  - run-analyzer-recipe
affects:
  - .claude/commands/run-analyzer.md
tech_stack_added: []
patterns_used:
  - probe-and-dispatch transport (bq_cli vs bq_mcp at runtime)
  - in-memory `${BQ_DATASET}` substitution before query dispatch
  - partial-state try/finally pattern guaranteeing summary.json always lands
  - artifact-write order (queries -> report -> Skill -> summary.json LAST)
key_files_created:
  - .claude/commands/run-analyzer.md
key_files_modified: []
decisions:
  - Used ASCII hyphen in the inline Task-1 placeholder ("Steps 5-7") instead of the en dash the plan used in its own text; the "no em/en dashes anywhere" check is stricter than the placeholder pattern the plan literally suggested.
  - Steps 2 and 3 distinguish bq_cli stderr capture (`*.stderr` sidecar) from bq_mcp tool-response error handling; the recipe documents both branches explicitly rather than abstracting them away.
  - Recipe references the `write-notion-report` Skill response shape (with `skill_unavailable` as a category the recipe synthesizes when the Skill itself is missing from the session) rather than waiting for a Plan 02 contract probe.
metrics:
  duration_seconds: 181
  tasks_completed: 2
  tasks_total: 2
  completed_date: 2026-05-25
---

# Phase 1 Plan 3: /run-analyzer recipe Summary

A single self-contained 128-line `.claude/commands/run-analyzer.md` that runs the weekly channel-patterns analyzer end to end: preflight env-var checks, runtime transport probe (bq CLI or BigQuery MCP), data-health pull, top-videos pull, six-section Phase-1 report draft, strict 8-key dict assembly, write-notion-report Skill invocation, and a summary.json write that lands even when earlier steps throw. No project-local @-imports, so the file is copy-pasteable into a claude.ai cloud routine (D-06).

## Tasks Completed

| Task | Name | Commit |
|------|------|--------|
| 1 | Author the /run-analyzer recipe with preflight, transport probe, data-health, top-videos pull, and report draft | f37fab8 |
| 2 | Add report-dict assembly, Skill invocation, summary.json write, and operator-message step | 2b695ae |

## Files Created

- `.claude/commands/run-analyzer.md` (128 lines) — the slash-command recipe. Frontmatter sets `disable-model-invocation: true` because the recipe has Notion + filesystem side effects. Body is a `# /run-analyzer` heading followed by Steps 0 through 8 (9 sections total), each ~10-20 lines. No project-local @-imports anywhere in the body; the file is fully transportable into a cloud routine that cannot resolve them.

## Files Modified

None. The recipe is a single new file; no existing files were touched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] The plan's own placeholder note used an en dash that the plan's own check 10 forbids.**

- **Found during:** Task 1 verification (Check 10 fails when Check 11's accepted form is `Steps 5–7`).
- **Issue:** The plan text instructs writing the placeholder as `<!-- Steps 5–7 added in Task 2 -->` (with U+2013 en dash) and then check 10 asserts `! grep -P "[—–]" "$F"` — i.e., no em or en dash anywhere in the file. With `set -e`, `! grep ...` returns success when grep finds nothing, so the negated form silently passes when the en dash IS present because of how bash interacts with negated commands (the `!` form short-circuits `set -e` errexit behavior in bash). Verified by running the negated grep with explicit exit-code check: `grep -P "[—–]" "$F"` returns exit 0 (match found) and `! grep -P "[—–]" "$F" > /dev/null` returns exit 1.
- **Fix:** Used the ASCII-hyphen form `<!-- Steps 5-7 added in Task 2 -->` in the placeholder. The plan's check 11 already accepts either form (`grep -qF "Steps 5–7" || grep -qF "Steps 5-7"`), so this satisfies both checks. The placeholder is gone after Task 2 anyway, but the file would have shipped with an en dash if I had followed the plan text literally.
- **Files modified:** `.claude/commands/run-analyzer.md` (during Task 1, before commit).
- **Commit:** rolled into `f37fab8`.

### Architectural Changes

None.

## Auth Gates Encountered

None. The recipe does not execute any of its own steps at write time; the live BigQuery and Notion calls happen when an operator invokes `/run-analyzer` after Plan 02 ships the Skill.

## Comparison vs RESEARCH §5 outline

RESEARCH §5 sketched a recipe outline targeting ~110 lines with the same Step 0-8 structure. The actual recipe came in at 128 lines, within the D-02 range of 80-150. Material differences from the §5 sketch:

- **Step 1 transport probe**: §5 sketched `TRANSPORT=bq` / `TRANSPORT=mcp`. The recipe uses `TRANSPORT=bq_cli` / `TRANSPORT=bq_mcp` to match the `transport` field values in `runs/README.md` (extended in Plan 01-01). Same intent, names now align across the schema and the recipe.
- **Step 1 invocation shapes**: §5 deferred the BigQuery MCP argument shape to a Wave-0 probe. The recipe uses the probed shape verbatim from `01-01-PROBE-NOTES.md` — `{"projectId": "<value>", "query": "<SQL>"}` with both keys REQUIRED, and the response-row note about positional `{"f": [{"v": ...}, ...]}` arrays needing to be zipped against `schema.fields[].name` to recover column names. RESEARCH §4 hypothesized `{"sql", "project_id"}`; that hypothesis was wrong and the recipe does NOT reference it.
- **Step 2 failure routing**: §5 listed three failure categories (bq_auth, missing_table, empty_result) generically. The recipe adds the bq_cli stderr patterns explicitly (`Reauthentication failed`, `cannot prompt during non-interactive`, `Could not load the default credentials`) and notes the bq_mcp branch returns errors in the tool response rather than stderr.
- **Step 7 partial-state**: §5 documented this in prose; the recipe formalizes the contract with the file name (`.partial-state.json`), the append-on-success / read-on-throw / delete-after pattern, and explicitly notes the file is transient and never committed.
- **Step 8 operator messages**: §5 gave three patterns. The recipe uses the same three patterns verbatim. Added: explicit guidance that the BQ-FAIL pattern's `{relevant section}` is one of "BigQuery auth failure", "Required table is missing or empty", or "A required table is stale" — chosen by the error category from Step 2 or Step 3. This keeps the operator-message-to-runbook mapping deterministic.

## BigQuery MCP invocation path vs the inferred shape

RESEARCH §4 inferred `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly` arguments as `{"sql": "<SELECT ...>", "project_id": "<optional>"}` based on Google Cloud BigQuery MCP family conventions. The live probe in `01-01-PROBE-NOTES.md` found the actual shape is:

- `query` (not `sql`) — required.
- `projectId` (camelCase, not `project_id`) — required (the wrapper does NOT fall back to `gcloud config`).
- Response rows in BigQuery REST positional shape: `{"f": [{"v": "..."}, ...]}`. The recipe documents the zip-against-schema-fields step inline so an operator reading the file knows to recover column names from `schema.fields[].name` rather than from the row keys.
- `totalBytesBilled` / `totalBytesProcessed` returned as JSON strings; the recipe notes they must be coerced before any arithmetic (though Phase 1 does not do cost arithmetic, this guards Phase 3).

These corrections are encoded verbatim in Step 1 of the recipe; no part of the recipe uses the inferred-but-wrong shape.

## Operator-message text vs RESEARCH §5

The three operator-message patterns in the recipe match §5's text byte-for-byte for SUCCESS and NOTION-FAIL. The BQ-FAIL pattern adds the runbook-section selection rule explicitly (§5 had `'{relevant section}'` as a placeholder without specifying which section maps to which error category). The recipe enumerates the three valid sections and ties the choice to the Step 2 / Step 3 error category — this avoids future ambiguity when extending the recipe with new failure modes.

## Known Stubs

None. The recipe is a self-contained set of instructions and references real files (`sql/04_data_health_check.sql`, `sql/02_top_full_length_videos.sql`, `.claude/skills/write-notion-report/SKILL.md`, `docs/runbook.md`, `runs/README.md`). The Skill itself ships in Plan 02; if Plan 02 has not landed yet, the recipe's Step 6 will hit the `skill_unavailable` category and surface the operator message correctly. That is intentional behavior, not a stub.

## Threat Flags

None. The recipe does not introduce new security surface beyond what Plan 01-01 already accounted for in its threat model (T-01-03-01 through T-01-03-SC). The recipe substitutes only the literal `youtube_analytics` token with `$BQ_DATASET` (never operator input), writes only to repo-local paths formed from `run_date` (no traversal possible), and the Skill validates the dict before any Notion call.

## Self-Check: PASSED

- `.claude/commands/run-analyzer.md` — FOUND, 128 lines, NOT gitignored (`git check-ignore -q` exits 1).
- All step headings `## Step 0:` through `## Step 8:` — FOUND (9 headings).
- All 8 input-contract dict keys (run_date, data_health, headline, working, not_working, patterns, open_questions, markdown_body) — FOUND in Step 5 section.
- Literal strings `transport`, `notion_url`, `notion_write_ok`, `.partial-state` — all FOUND.
- `docs/runbook.md` references — FOUND 8 times (>= 3 required).
- No em/en dashes — VERIFIED via `grep -P "[—–]"` returning exit 1.
- No @-imports — VERIFIED via `grep -E "^@[A-Za-z]"` returning exit 1.
- No bare `NOTION_PAGE_ID` — VERIFIED via `grep -E "(^|[^_])NOTION_PAGE_ID([^_]|$)"` returning exit 1; only `NOTION_REPORT_PAGE_ID` appears.
- Error category names `env_missing`, `bq_auth`, `missing_table`, `empty_result`, `skill_unavailable`, `report_dict_invalid` — all FOUND.
- Commits `f37fab8`, `2b695ae` — FOUND via `git log --oneline`.
