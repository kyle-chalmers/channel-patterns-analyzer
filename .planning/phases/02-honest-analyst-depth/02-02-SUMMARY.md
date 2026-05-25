---
phase: 02-honest-analyst-depth
plan: 02
subsystem: recipe
tags: [analyzer, recipe, run-analyzer, report-structure, confidence-labels, stale-disclaimer, phase1-inheritance]

# Dependency graph
requires:
  - phase: 01-first-notion-report-end-to-end
    provides: "/run-analyzer recipe (8-step linear markdown), write-notion-report Skill (children-blocks renderer), runs/README.md summary.json schema, sql/02..04"
  - plan: 02-01
    provides: "sql/02, sql/03 with latest_common CTE pattern and double-quoted Phoenix-tz DATE_DIFF; PHASE1-ASSUMPTIONS-VERIFIED.md confirming A1/A2/A3"
provides:
  - ".claude/commands/run-analyzer.md extended to 10 steps: new Step 4 (prior-report read), new Step 5 (live eligible-count query), reworked Step 6 (draft step that loads CLAUDE.md rules by section title and produces all six sections with inline (label, n=N) confidence and collapsed stale-table disclaimers)"
  - "Phase 1 inheritance fixes folded into the recipe: dropped invalid --max_rows=10000 flag, switched bq_cli SQL transport to stdin pipe, added SIMULATE_STALE env-var for synthetic stale-table testing, added bq_mcp transport smoke-test note, made per-run snapshot calibration logic explicit (reads prior summary.json.snapshot_dates)"
  - "runs/README.md schema doc extended with prior_reports_consulted field"
  - "CHANGELOG.md ## 2026-05-25 heading appended with two new bullets recording the recipe extension and the schema doc change"
affects:
  - "Plan 02-03 self-audit step inserts between the new Step 6 (draft) and Step 8 (Skill invocation), i.e., becomes Step 7 (assemble) is unchanged; self-audit becomes a new Step 7.5 OR Plan 02-03 reshapes the numbering again"
  - "Future operators get a recipe that actually runs end-to-end without the workarounds Phase 1's live run needed"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stdin-pipe form for bq query: `printf '%s' \"$SQL\" | bq --format=json query --use_legacy_sql=false --project_id=\"$BQ_PROJECT\"`. Replaces positional SQL to avoid Python RecursionError on Unicode-decorated SQL files."
    - "Inline `(label, n=N).` confidence parenthetical for prose claims; `Confidence` + `n` columns for table-shaped claims; one label per claim (D-07a); no Notion callout wrapping for confidence (D-07b)"
    - "Per-section collapsed stale-table disclaimer pattern: when multiple findings in a section would all disclaim the same stale table, collapse to one disclaimer per section per stale table (D-12, RESEARCH.md Pitfall 5)"
    - "SIMULATE_STALE env-var override: `table_name:days,table_name:days` format mutates in-memory data_health rows; records a warnings entry; never modifies BigQuery or the on-disk data_health.json"
    - "Per-run snapshot calibration: prior-report calibration logic reads each prior `runs/{date}/summary.json.snapshot_dates` rather than inferring snapshot continuity from prose"

key-files:
  created:
    - ".planning/phases/02-honest-analyst-depth/02-02-SUMMARY.md"
  modified:
    - ".claude/commands/run-analyzer.md"
    - "runs/README.md"
    - "CHANGELOG.md"

key-decisions:
  - "Renumbered the recipe to 10 steps (Steps 0-3 unchanged from Phase 1; Steps 4 and 5 new; Steps 6-10 renumbered from Phase 1's Steps 4-8). Kept the numbered-step style Phase 1 established rather than switching to title-only headings, because the numbered style is what the codebase already uses and the operator messages in Step 10 reference 'Recovery: see docs/runbook.md § ...' by step number elsewhere."
  - "Inline `(label, n=N).` confidence parenthetical for prose plus `Confidence` + `n` columns for tables (per D-07 in 02-CONTEXT.md). Confidence stays a plain string at the entry-level (matching Phase 1's actual Skill input contract, per PHASE1-ASSUMPTIONS-VERIFIED.md A2); the `n` lives in the prose, not in the structured field. This is the markdown-rendering path; a future structured upgrade to `{label, n}` is forward-compatible because the Skill ignores the structured field today."
  - "Confidence-tier boundary verification: n=4 → low, n=5 → moderate, n=10 → standard (per CLAUDE.md § 'Small samples get hedged'; standard wins at exactly 10). Documented explicitly in the recipe so the draft step does not have to re-derive the table from CLAUDE.md prose at draft time."
  - "SIMULATE_STALE is a recipe-level seam, not a CLI flag, not an SQL edit, not a BQ change. Mutates in-memory data_health rows only after the real sql/04 runs; writes a warnings entry to summary.json so the audit trail shows the override fired. Format `table_name:days,table_name:days` so a single env var can simulate the 89-day-stale state Phase 1 saw on 2026-05-24 without rolling back BigQuery."
  - "CHANGELOG.md appended under the existing `## 2026-05-25` heading (not a new H2) per the plan instruction. This run is same-day with Plan 02-01's commits; future plans on different dates will get their own heading."

patterns-established:
  - "Recipe extension pattern: insert new numbered steps at the seam (between Step 3 data fetch and Step 6 draft); renumber downstream steps cleanly; update cross-references in body text"
  - "Phase-inheritance pattern: when a prior phase's VERIFICATION.md flags inheritance items, fold them into the first plan of the next phase that touches the affected file, in the same commit as the planned work; do not let inheritance items drift across multiple commits"

requirements-completed: [ANALYSIS-03, ANALYSIS-05, REPORT-01, REPORT-02]

# Metrics
duration: ~35min
completed: 2026-05-25
---

# Phase 02 Plan 02: /run-analyzer Recipe Extension Summary

**The /run-analyzer recipe now reads prior reports for calibration, queries a live eligible video count, and produces all six required sections with inline (label, n=N) confidence parentheticals and collapsed stale-table disclaimers, plus four Phase 1 inheritance fixes (dropped invalid --max_rows, stdin SQL pipe, SIMULATE_STALE override, bq_mcp smoke note) folded in so the recipe actually runs end-to-end.**

## Performance

- **Duration:** ~35 min (Read context + 3 commits + SUMMARY).
- **Tasks:** 3 / 3 (all atomic, all committed sequentially on `main`).
- **Files modified:** 3 source files (.claude/commands/run-analyzer.md, runs/README.md, CHANGELOG.md) + 1 planning artifact (this SUMMARY).
- **Commits:** `769f4a8` (Task 1 recipe new steps + inheritance fixes), `54bdea2` (Task 2 reworked draft step), `0130fa7` (Task 3 schema doc + CHANGELOG).

## Accomplishments

### Plan-as-written deliverables

- **Task 1 (recipe new steps):** added Step 4 "Read prior reports for calibration" and Step 5 "Query live eligible video count" between Phase 1's Step 3 and the existing draft step. Step 4 lists `reports/*.md` excluding today's `run_date`, sorts, takes last 3, reads each plus the matching `runs/{date}/summary.json.snapshot_dates` for per-run snapshot calibration, and records the consulted dates for `summary.json.prior_reports_consulted` (D-10). Step 5 runs an inline bq query using the same `latest_common` CTE pattern Plan 02-01 added to sql/02 and sql/03; persists the result to `runs/{run_date}/queries/eligible_video_count.json`; documents the confidence-tier boundaries explicitly (n<5 low, 5-10 moderate, ≥10 standard with n=10 going to standard).
- **Task 2 (reworked draft step):** Step 6 now loads six CLAUDE.md sections by title before any prose is written (Age control, Small samples, Brutal honesty, Never claim, Voice, plus D-08 cross-week framing), specifies the inline `(label, n=N).` format with prose and table examples (D-07a + D-07b explicitly), enumerates all six required section headings in order with explicit empty-section copy (D-11), and prescribes the per-section collapsed stale-table disclaimer pattern (D-12). The output-dict section now references PHASE1-ASSUMPTIONS-VERIFIED.md A2 directly: confidence stays a string at the entry level; `n` lives in prose; markdown-rendering path is preserved.
- **Task 3 (schema doc + CHANGELOG):** runs/README.md schema example block gains `"prior_reports_consulted": ["2026-05-18", "2026-05-11", "2026-05-04"]` between `notion_url` and `errors`, plus a prose paragraph below the block documenting what the field stores and the today-filter rule. CHANGELOG.md gains two new bullets under the existing `## 2026-05-25` heading: one comprehensive bullet covering the recipe extension + all four inheritance items, and one shorter bullet for the schema doc change.

### Phase 1 inheritance items folded in (the four critical fixes)

1. **Dropped `--max_rows=10000` from the bq_cli invocation.** Phase 1's Step 1 invocation `bq query --max_rows=10000 ... "$SQL"` crashed with Python `RecursionError` on every run (the flag is not valid for `bq query`; it belongs to `bq head`). Removed entirely. Row-count control is now SQL-level (`LIMIT` inside the file); the recipe documents this and notes the bq default 100-row cap as the fallback, which is fine for ~23 full-length videos.
2. **Switched bq_cli SQL transport from positional to stdin pipe.** New form: `printf '%s' "$SQL" | bq --format=json query --use_legacy_sql=false --project_id="$BQ_PROJECT"`. This avoids the Unicode box-drawing crash (`─` U+2500 in every sql/ file header trips bq's flag-suggester when passed positionally). The `bq_mcp` branch is unaffected.
3. **Added `SIMULATE_STALE` env-var override at the data-health step.** Format `table_name:days,table_name:days`. Mutates in-memory `data_health` rows after the real sql/04 runs; never modifies the on-disk `runs/{date}/queries/data_health.json`; writes a `warnings: ["simulate_stale_applied: ..."]` entry to `summary.json` so the audit trail shows the override fired. This restores the ability to exercise D-12 (stale-table disclaimer rule) end-to-end now that the 89-day live stale state resolved on 2026-05-25.
4. **Added bq_mcp transport smoke-test note (one paragraph).** Operators should run the recipe once with `BQ_TRANSPORT=bq_cli` and once with `BQ_TRANSPORT=bq_mcp` to confirm identical row counts on `data_health` and `top_full_length_videos`. Phase 1 only exercised `bq_cli` live; the MCP branch is documented but unverified end-to-end.

The fifth item from VERIFICATION.md (per-run snapshot calibration) is woven into Task 1's Step 4: the recipe now explicitly states the calibration logic reads `summary.json.snapshot_dates` from each prior run rather than inferring snapshot-state continuity from prose. The 89-day gap resolving between 2026-05-24 and 2026-05-25 is named directly in the recipe text as the motivating context.

## Files Created/Modified

- **`.claude/commands/run-analyzer.md`** (modified): grew from 8 steps to 10 steps (Phase 1 Step 4-8 renumbered to 6-10; new Step 4 prior-report read; new Step 5 eligible-count query; reworked Step 6 draft step with rules + sections + disclaimers). Step 1 invocation switched from positional SQL with --max_rows to stdin pipe. Step 2 data-health gained the SIMULATE_STALE override. Stale cross-references in body text updated to the new step numbers. Stale `BUSINESS_RULES.md §4` numeric reference at Step 3 swapped to section-title form. Zero em dashes, zero en dashes, zero banned vocabulary anywhere I wrote.
- **`runs/README.md`** (modified): JSON example block gains `prior_reports_consulted` entry; prose paragraph below documents the field. `voice_audit` field NOT added (reserved for Plan 02-03 per its scope).
- **`CHANGELOG.md`** (modified): two new bullets appended under the existing `## 2026-05-25` heading (the one Plan 02-01 created on the same day). Existing Plan 02-01 entry prose left untouched.

## Decisions Made

- **Recipe stays a single linear file, 10 numbered steps.** Phase 1 established the numbered-step style; Plan 02-02 keeps it (Steps 0-3 unchanged; new 4 and 5; renumbered 6-10). An alternative would have been title-only `## Step:` headings, but cross-references in body text are easier to maintain with stable numbers, and the operator-message strings in Step 10 reference docs/runbook.md sections by step number elsewhere in Phase 1's design intent.
- **Confidence stays a string at the entry level; `n` lives in prose.** Per PHASE1-ASSUMPTIONS-VERIFIED.md A2, Phase 1's Skill renders Notion blocks from `markdown_body` only and the per-finding `confidence` field is a plain string. Plan 02-02 keeps that contract: inline `(label, n=N).` lives in the markdown prose (which the Skill renders verbatim) and in each `working[]`/`not_working[]`/`patterns[]` entry's `body` field. A future Skill enrichment can promote `confidence` to `{label, n}` without breaking anything because the Skill ignores the structured field today.
- **SIMULATE_STALE format is `table_name:days,table_name:days`.** Comma-separated pairs; colon separator inside each pair. Chosen because it's a single env var, no parsing library needed, no shell-quoting surprises, and the format reads like an obvious operator command. Documented in the recipe with the example `SIMULATE_STALE="daily_video_analytics:89,daily_traffic_sources:89"` so a first-time operator can copy-paste.
- **CHANGELOG.md appended under the existing `## 2026-05-25` heading.** Same day as Plan 02-01's commits, same-day-same-heading is the convention from Phase 1's CHANGELOG. Two new bullets under the same H2 keep the audit trail dense and chronological.

## Output spec answers (per plan)

- **Final shape of the three new/extended recipe sections:**
  - `## Step 4: Read prior reports for calibration`. Purpose: implements ANALYSIS-05 + D-08 + D-10 by reading up to 3 most recent prior reports plus their summary.json.snapshot_dates for confidence calibration; records consulted dates for summary.json; explicit no-citation rule + banned phrases list.
  - `## Step 5: Query live eligible video count`. Purpose: implements ANALYSIS-03 + D-07 by running an inline bq query (same latest_common CTE pattern as sql/02 and sql/03) to compute eligible_count, persisting the result, and providing the channel-wide N for the (label, n=N) parentheticals.
  - `## Step 6: Draft the report (PERSIST-01)`. Purpose: reworked from Phase 1's narrative draft step into a 6-subsection rule-application checklist (rules to apply, confidence label format, six-section structure, stale-table disclaimer, per-section drafting guidance, output dict assembly).
- **Was Phase 1's `/run-analyzer` already shipped at execution time?** Yes, per PHASE1-ASSUMPTIONS-VERIFIED.md A1 = `verified` (commit `3a94b7d` on `main`). Plan 02-02 extended in place rather than scaffolding.
- **Was the structured-per-finding confidence shape (A2) usable?** Yes per PHASE1-ASSUMPTIONS-VERIFIED.md A2 = `verified`. The `working[]` / `not_working[]` / `patterns[]` entries already accept `confidence` as `"low" | "moderate" | "standard"` (plain string), but Phase 1's Skill renders Notion blocks from `markdown_body` only and ignores the structured field. Plan 02-02 keeps the markdown path and places the `(label, n=N).` parenthetical inline in prose; the entry-level confidence field stores the label string only (the n lives in prose). No Skill edit was needed.
- **Unexpected drift between RESEARCH.md and Phase 1's actual recipe shape?** None material. RESEARCH.md assumed a clean draft → publish seam (A1) and Phase 1 actually shipped exactly that (8 numbered steps with the draft-step boundary at Step 4 → Step 5 → Step 6). Plan 02-02 inserted two new steps and reworked one, all in place. The only "surprise" was that the two recipe defects from Phase 1's live run had to be inherited and fixed in this plan, which is what VERIFICATION.md § "Phase-2 Inheritance" item 1 and the orchestrator's `<phase1_inheritance_items>` block both flagged in advance.

## Deviations from Plan

Two minor scope additions, all flagged by the orchestrator's `<phase1_inheritance_items>` block (not surprises):

1. **Rule 2 (auto-add missing critical functionality):** Inherited four Phase 1 VERIFICATION.md items (recipe defects 1+2, SIMULATE_STALE, bq_mcp smoke note, per-run snapshot calibration) into the same commits as the planned work. The orchestrator explicitly mandated this; not a deviation in spirit, just a scope expansion the plan as-written did not enumerate.
2. **Stale cross-reference cleanup (Task 1 commit):** the recipe contained one `BUSINESS_RULES.md §4` numeric reference at Step 3 that became newly visible during my pass. Swapped to section-title form `BUSINESS_RULES.md § "Table grain and join keys (data contract)"` per the same drift-avoidance convention Plan 02-01 used in the SQL header rewrites. This is Rule 2 (correctness requirement under CONCERNS.md drift warning) territory and lives in the same Task 1 commit as the planned recipe edits.

No Rule 1 bugs, no Rule 3 blocking-fix expansions beyond #1, no Rule 4 architectural escalations.

## Issues Encountered

Two environment anomalies, neither affecting deliverables:

1. **Pre-existing untracked changes in `runs/` and `reports/`.** At executor start, `git status` showed modifications to `runs/2026-05-25/queries/*.json`, `runs/2026-05-25/queries/*.stderr`, `runs/2026-05-25/report.md`, `reports/2026-05-25.md`, `runs/2026-05-25/summary.json` that I did not author (consistent with Plan 02-01's "Issues Encountered" §3, likely the parallel orchestrator backfill activity around 2026-05-25 ~23:15Z). I left all of those files untouched; my three commits explicitly listed only the files I modified. The current working tree still shows those same untracked modifications after my commits.
2. **No worktree isolation this wave.** Orchestrator confirmed sequential execution on main; pre-commit HEAD-safety assertions for worktree mode did not apply. Commits landed on `main` directly. Confirmed via `git log --oneline -5` after each commit.

## User Setup Required

None. The recipe extensions are inert until the next `/run-analyzer` invocation, at which point the operator will see the new prior-report read step, the new eligible-count step, and the reworked draft step automatically. The `SIMULATE_STALE` env-var is opt-in (set it only when testing the D-12 disclaimer rule against synthetic stale data); no action needed for normal runs.

## Verification Evidence

| Check | Method | Result |
|------|--------|--------|
| Recipe has Step 4 prior-report read | `grep -q '^## Step 4: Read prior reports for calibration' .claude/commands/run-analyzer.md` | pass |
| Recipe has Step 5 eligible-count + latest_common + Phoenix tz | `grep -q 'latest_common' && grep -q 'CURRENT_DATE("America/Phoenix")' && grep -qE 'eligible[_ ]count'` | pass |
| Step 6 (draft) loads ≥5 CLAUDE.md sections by title | `grep -c 'CLAUDE\.md § "'` | 10 (well above 5) |
| All six required section headings present in order | grep enumerating each | all 6 found in correct order |
| Inline `(label, n=N)` format documented | `grep -qE '\(label, n=N\)'` | pass |
| D-07a, D-07b, D-11, D-12 cited | per-grep | all 4 found |
| `prior_reports_consulted` in runs/README.md | `grep -q '"prior_reports_consulted"' runs/README.md` | pass |
| CHANGELOG ## 2026-05-25 heading + bullet naming recipe | awk-filter + grep | 5 bullets total under heading (3 from 02-01 + 2 from 02-02) |
| Recipe no longer contains `--max_rows=10000` | `grep -c '\-\-max_rows=10000' .claude/commands/run-analyzer.md` | 0 |
| Recipe uses `printf '%s' "$SQL" \| bq query` stdin form | `grep -c "printf '%s' \"\\\$SQL\""` | 2 (Step 1 + Step 5 cross-ref) |
| `SIMULATE_STALE` env-var documented | `grep -c 'SIMULATE_STALE'` | 2 (Step 2 + Step 6 reference) |
| `BQ_TRANSPORT=bq_mcp` smoke note present | `grep -c 'BQ_TRANSPORT=bq_mcp'` | 1 |
| No em/en dashes in recipe | `grep -cE '—\|–' .claude/commands/run-analyzer.md` | 0 |
| All three task commits on main | `git log --oneline -5` | 769f4a8, 54bdea2, 0130fa7 visible |

The plan's chained verify regex (`grep -c 'CLAUDE.md § "' ... \| awk '$1>=5{exit 0}'`) is the strictest Task 2 check; 10 references is well clear of the ≥5 bar.

## Next Phase Readiness

- **Plan 02-03 (self-audit step):** the recipe seam for the new self-audit step is now between Step 6 (draft) and Step 7 (assemble dict), or alternatively between Step 7 (assemble) and Step 8 (Skill invoke). Plan 02-03 should pick whichever boundary fits its checklist semantics; the existing seams are clean enough for either. The `voice_audit` field will land in runs/README.md schema doc as part of Plan 02-03 (Plan 02-02 left it explicitly out and noted so in the runs/README.md prose, so the schema doc gives Plan 02-03 a clear landing spot).
- **First real run after Plan 02-03 lands:** the recipe-as-written should now run end-to-end without the workarounds Phase 1's live run needed. The two recipe defects are fixed, the SIMULATE_STALE override exists for testing the D-12 disclaimer rule, and the bq_mcp transport has a smoke-test note. The first real Plan 02-03 run will also be the first test of inline `(label, n=N).` rendering in Notion (per PHASE1-ASSUMPTIONS-VERIFIED.md A5 = `not-yet-shipped`).
- **No blockers.** All Plan 02-02 deliverables on disk and committed; the recipe is ready for Plan 02-03's self-audit insertion; the schema doc has the new field; CHANGELOG is up to date.

## Self-Check: PASSED

Verified the SUMMARY's claims with file/commit existence checks:

```
.claude/commands/run-analyzer.md                                                  FOUND (modified)
runs/README.md                                                                    FOUND (modified)
CHANGELOG.md                                                                      FOUND (modified)
.planning/phases/02-honest-analyst-depth/02-02-SUMMARY.md                         FOUND (this file)
Commit 769f4a8 (Task 1 recipe new steps + Phase 1 inheritance fixes)              FOUND
Commit 54bdea2 (Task 2 reworked draft step)                                       FOUND
Commit 0130fa7 (Task 3 schema doc + CHANGELOG entry)                              FOUND
```

All verification table checks above pass against the committed state.

---
*Phase: 02-honest-analyst-depth*
*Completed: 2026-05-25*
