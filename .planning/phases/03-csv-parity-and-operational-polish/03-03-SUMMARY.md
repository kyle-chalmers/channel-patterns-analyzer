---
phase: 03-csv-parity-and-operational-polish
plan: 03
subsystem: recipe-and-operator-docs
tags: [csv-parity, cloud-routine, run-now-checklist, env-cleanup, voice-rules]
requires: [03-01, 03-02]
provides:
  - csv-end-to-end-recipe-branch
  - cloud-routine-setup-walkthrough
  - run-now-checklist
  - minimal-env-example
affects:
  - .claude/commands/run-analyzer.md
  - docs/schedule.md
  - .env.example
  - CHANGELOG.md
tech_stack_added: []
patterns_used:
  - short-circuit transport probe (DATA_SOURCE=csv before bq probe)
  - dispatch-call-site sentence per transport (Steps 2/3/5)
  - numbered cloud-UI walkthrough with concrete field names
  - checkbox Run-now smoke test linked to runbook anchors
  - boxed-divider .env section comments
  - CHANGELOG before/after/Impact bullet shape
key_files_created: []
key_files_modified:
  - .claude/commands/run-analyzer.md
  - docs/schedule.md
  - .env.example
  - CHANGELOG.md
decisions:
  - "Honored D-02-R (the plan's cloud-paste-safety decision): the recipe must contain zero .planning/ references after this plan"
  - "Honored D-01: cloud routine uses the BigQuery web connector, never a service-account key (table cell in docs/schedule.md fixed accordingly)"
  - "Honored Open Question 3 short-circuit recommendation: DATA_SOURCE=csv short-circuits BEFORE the bq probe (no parallel probe, no double-success)"
  - "Honored Open Question 6 REMOVE recommendation: four unused env vars stripped from .env.example rather than wired through"
  - "Applied Rule 2 (correctness via voice rules): removed em dashes from docs/schedule.md and .env.example that pre-dated this plan but violate CLAUDE.md § Voice — the plan's acceptance criteria explicitly require zero em dashes in the final state of these files"
metrics:
  duration_sec: 306
  duration_min_approx: 5
  tasks_completed: 4
  files_modified: 4
  files_created: 0
  completed_date: "2026-05-26T04:10:00Z"
---

# Phase 3 Plan 03-03: CSV recipe branch, cloud routine walkthrough, env trim Summary

The recipe now branches three ways at Step 1 (`csv`, `bq_cli`, `bq_mcp`), dispatches CSV queries through `python scripts/csv_query.py` at Steps 2/3/5, and is fully self-contained for cloud paste (zero `.planning/` references). `docs/schedule.md` carries a 9-step claude.com walkthrough plus a 4-item Run-now smoke test, with the Local-vs-cloud table corrected to point at the BigQuery web connector instead of the no-longer-used service-account key path. `.env.example` is down to the four env vars the recipe actually reads. Slice 1 (CSV end-to-end) and Slice 2 (cloud routine launchable) of MVP Phase 3 are complete; Slice 3 (runbook deepening) remains for Plan 03-04.

## What landed (per task)

### Task 1: `.claude/commands/run-analyzer.md` (commit `3ec3ddc`)

Five edit groups applied:

- **Group A.** New first-position probe bullet at Step 1 (above the `command -v bq` line): if `DATA_SOURCE=csv`, set `TRANSPORT=csv`, SKIP the BigQuery probe, and regenerate `sample_data/*.csv` via `python scripts/csv_fallback_loader.py` before Step 2. The bullet documents the stable seeds (`Random(42)/43/44`) and the operator escape hatch (`python scripts/csv_fallback_loader.py --snapshot-date YYYY-MM-DD` for stale-data testing). Explicit short-circuit framing prevents the dual-success failure mode where `bq` would also succeed on a developer machine.
- **Group B.** New `csv` invocation-shape bullet under "Invocation shapes (use verbatim)": `python scripts/csv_query.py <query_name>` for `data_health`, `top_full_length_videos`, `eligible_video_count`. Documents that the helper outputs the same JSON array shape as `bq --format=json query` and writes to the same `runs/{run_date}/queries/<query_name>.json` path. No `.stderr` sidecar.
- **Group C.** Dispatch sentences added to Steps 2, 3, 5. Each call site says "When `$TRANSPORT=csv`, the dispatch is `python scripts/csv_query.py <name>`. Same output path."
- **Group D.** New sub-bullet under Step 6 § "1. Rules to apply before writing prose": "**CSV-mode annotation.** When `$TRANSPORT=csv`, the report's first line (above the `## Data Health` heading) reads exactly `data source: csv (sample fixtures, not live)`." The only structural difference between a CSV-mode and BigQuery-mode report.
- **Group E.** Six `.planning/` prose references dereferenced. Pre-edit locations (line numbers refer to the file as it was in this worktree, post-rebase, pre-edit):

  | Pre-edit line | Reference | Replacement |
  |---|---|---|
  | 82 (Step 4 intro) | "ANALYSIS-05 and D-08 from `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`" | "ANALYSIS-05 (read prior reports for confidence calibration) and the prior-report citation rule" |
  | 170 (Step 6 intro) | "(per `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`)" parenthetical | parenthetical removed |
  | 181 (Step 6 §1 last bullet) | "Apply D-08 from `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`" | "Apply the prior-report citation rule" |
  | 250 (Step 7 intro) | "D-01 Layer 2 from `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`" | "the self-audit gate (Layer 2 of the voice-and-structure verification)" |
  | 252 (Step 7 description, first parenthetical) | "(cited in `.planning/phases/02-honest-analyst-depth/02-RESEARCH.md` § 'Common Pitfalls' 3)" | parenthetical removed |
  | 252 (Step 7 description, mirrors clause) | "mirrors `CLAUDE.md` and `02-CONTEXT.md` rules 1:1" | "mirrors `CLAUDE.md` rules 1:1" |

After all six: `grep -nF '.planning/' .claude/commands/run-analyzer.md` returns zero matches. SIMULATE_STALE block (the old lines 51-59 in the pre-edit file) unchanged. Existing `bq_cli` and `bq_mcp` invocation-shape bullets unmodified.

### Task 2: `docs/schedule.md` (commit `acaa2f8`)

Four edit groups applied:

- **Group A — portability bug fix.** Local-vs-cloud table BigQuery-auth cell changed from "Service account key in routine env vars" to "BigQuery web connector (authorized once in your Anthropic account)" per D-01. The rest of the table stays.
- **Group B — new "Cloud routine setup walkthrough" section.** 9 numbered steps, with the following field names verified against `https://code.claude.com/docs/en/routines` on 2026-05-26:

  | # | Field | Value / instruction |
  |---|---|---|
  | 1 | Connectors authorization | Authorize BigQuery (Google Cloud) and Notion in claude.com → Settings → Connectors |
  | 2 | Routines page | claude.com → Settings → Routines → New Routine |
  | 3 | Routine name | `channel-patterns-analyzer-weekly` |
  | 4 | Instructions | paste full contents of `.claude/commands/run-analyzer.md`; do not edit after pasting |
  | 5 | Repositories | select `channel-patterns-analyzer` (required for Step 4 prior-reports read) |
  | 6 | Trigger | Schedule, Weekly, Monday, 9:00 AM, America/Phoenix |
  | 7 | Connectors | verify BigQuery + Notion; remove unrelated |
  | 8 | Environment variables | `NOTION_REPORT_PAGE_ID`, `BQ_PROJECT`, `BQ_DATASET` (placeholder values only) |
  | 9 | Click Create | (close action) |

- **Group C — new "Run-now checklist" section.** 4 checkbox items prefixed `(a)/(b)/(c)/(d)`. Each links to a current `docs/runbook.md` section by anchor (e.g., "Notion write failed"). Closing sentence notes that the additional failure modes will get runbook sections in Plan 03-04 (intentionally not pre-linked to avoid dangling-anchor warnings).
- **Group D — preserve existing sections.** "What the routine does", "Re-running manually", "Changing the schedule", "Reference" all preserved verbatim (with em-dash voice-rule cleanup; see Deviations below).

### Task 3: `.env.example` (commit `dc7566e`)

Four unused env vars removed:

- `YOUTUBE_CHANNEL_ID` (no code reads it)
- `ANALYSIS_LOOKBACK_DAYS` (no code reads it)
- `MIN_VIDEO_AGE_DAYS` (no code reads it; 14-day age filter is hardcoded in sql/02 + sql/03 + the inline eligible_count SQL in the recipe Step 5)
- `SCHEDULE_TIMEZONE` (no code reads it; Phoenix is hardcoded everywhere)

Now-empty section headings dropped:

- `# ─── YouTube channel identity ───` (only held `YOUTUBE_CHANNEL_ID`)
- `# ─── Analysis configuration ───` (held the other three)

Four real env vars remain (`DATA_SOURCE`, `BQ_PROJECT`, `BQ_DATASET`, `NOTION_REPORT_PAGE_ID`) under three section headings (Data source mode, Google Cloud / BigQuery, Notion). The recipe-reads set and `.env.example` declared set match 1:1. File length down from 39 lines to 22.

### Task 4: `CHANGELOG.md` (commit `4c3a07d`)

New H2 inserted at top: `## 2026-05-25, Phase 3 Plan 03-03`. One framing paragraph followed by four bullets (one per modified file plus one for the indirect cross-plan integration). Each bullet uses the before/after/Impact discipline established by the Phase 2 entries above it.

Note: the wave-1 H2 (`## 2026-05-25, Phase 3` or similar) that Plans 03-01 and 03-02 would have added is not present in this worktree's CHANGELOG because the worktree branched before wave 1 merged to main. The orchestrator's merge step is expected to either fold this plan's H2 into the wave-1 H2 (one date, one H2 per project convention) or leave both as sibling H2 headings under today's date. Either outcome is acceptable.

## Six dereferenced `.planning/` references (per plan output spec)

Already enumerated in the Task 1 section above; restated here as the canonical list per the plan's output spec:

1. Pre-edit line 82: Step 4 intro, `02-CONTEXT.md` reference removed.
2. Pre-edit line 170: Step 6 intro, `02-CONTEXT.md` parenthetical removed.
3. Pre-edit line 181: Step 6 § 1 last bullet, `02-CONTEXT.md` reference removed.
4. Pre-edit line 250: Step 7 intro, `02-CONTEXT.md` reference removed.
5. Pre-edit line 252: Step 7 description, `02-RESEARCH.md § "Common Pitfalls" 3` parenthetical removed.
6. Pre-edit line 252: Step 7 description, `02-CONTEXT.md` removed from the "mirrors CLAUDE.md and 02-CONTEXT.md rules 1:1" clause.

Final grep: `grep -nF '.planning/' .claude/commands/run-analyzer.md` returns zero matches.

## Final shape of the schedule.md walkthrough (per plan output spec)

9 numbered steps; per-step field name and instruction enumerated in the Task 2 § "Group B" table above.

## Removed and remaining env vars (per plan output spec)

Removed: `YOUTUBE_CHANNEL_ID`, `ANALYSIS_LOOKBACK_DAYS`, `MIN_VIDEO_AGE_DAYS`, `SCHEDULE_TIMEZONE`.

Remaining: `DATA_SOURCE`, `BQ_PROJECT`, `BQ_DATASET`, `NOTION_REPORT_PAGE_ID`.

The remaining set is exactly what `grep -oE 'DATA_SOURCE|BQ_PROJECT|BQ_DATASET|NOTION_REPORT_PAGE_ID' .claude/commands/run-analyzer.md | sort -u` returns.

## CSV-mode smoke test status

**Deferred.** The plan's verification block lists a live CSV-mode smoke test ("set `DATA_SOURCE=csv` in `.env`, invoke the recipe, confirm `reports/{date}.md` carries the six sections plus the top-of-report data-source line, and that the three `runs/{date}/queries/*.json` files parse as JSON arrays of dicts with string values"). This was not run live as part of this executor session for two reasons:

1. **Environment.** The executor runs in a non-interactive worktree with no `claude` CLI session available to invoke `/run-analyzer`. The recipe is designed to run inside a Claude Code session that loads `.claude/skills/write-notion-report` and either the `bq` CLI or the BigQuery MCP. Outside that context, the recipe cannot run end-to-end.
2. **Wave dependency.** The full CSV-mode chain depends on `scripts/csv_query.py` (Plan 03-02) being on `main`. This worktree branched before wave 1 (Plans 03-01 and 03-02) merged to `main`, so `scripts/csv_query.py` does not exist in this worktree's filesystem. The recipe's CSV invocation shape references it correctly, but a smoke test run from this worktree would `FileNotFoundError`.

**Recommended smoke test (operator-side, after this plan merges and wave 1 + wave 2 are on `main`):**

```bash
# 1. Switch to CSV mode locally.
echo "DATA_SOURCE=csv" >> .env

# 2. Regenerate fixtures (also exercised automatically by the recipe in Step 1).
python scripts/csv_fallback_loader.py

# 3. Invoke the recipe in a fresh Claude Code session.
claude
> /run-analyzer

# 4. Verify:
#    - reports/$(TZ=America/Phoenix date +%Y-%m-%d).md exists
#    - First line of that file: "data source: csv (sample fixtures, not live)"
#    - The six section headings (## Data Health, ## Headline, ## What is working,
#      ## What is not working, ## Patterns worth watching, ## Open questions)
#    - runs/$(TZ=America/Phoenix date +%Y-%m-%d)/queries/data_health.json,
#      top_full_length_videos.json, eligible_video_count.json each parses
#      as a JSON array of dicts with all-string values.
```

A BigQuery-mode regression test (run the recipe with `DATA_SOURCE` unset and confirm byte-identical behavior to Phase 2's last run) is also recommended but deferred for the same reasons.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Correctness] Remove pre-existing em dashes from `docs/schedule.md`**
- **Found during:** Task 2 pre-edit grep.
- **Issue:** The plan's acceptance criterion `grep -nF '—' docs/schedule.md` returning ZERO matches asserted that the pre-edit file had no em dashes. The pre-edit file actually had 5 em dashes (lines 3, 16, 27, 43, 47, 48) plus one en dash on line 11. The plan's planning-time reading was incorrect.
- **Fix:** Replaced em dashes with commas or sentence breaks per CLAUDE.md § "Voice". The en dash in "3–4 reports" became "3 to 4 reports".
- **Rationale:** CLAUDE.md § "Voice" (project-level) bans em dashes; the plan's success criterion explicitly required zero em dashes in the file's final state. Leaving the pre-existing em dashes would have failed the acceptance check even though they were not added by this plan.
- **Files modified:** `docs/schedule.md`
- **Commit:** `acaa2f8`

**2. [Rule 2 — Correctness] Remove pre-existing em dashes from `.env.example`**
- **Found during:** Task 3 pre-edit read.
- **Issue:** Pre-edit `.env.example` had 4 em dashes in header comments (lines 1, 3, 6, 7, 27). Plan acceptance required `grep -nF '—' .env.example` to return zero.
- **Fix:** Replaced em dashes with commas/colons in the comment lines. Final file has zero em dashes.
- **Files modified:** `.env.example`
- **Commit:** `dc7566e`

### Plan/reality drift notes (not deviations from intent)

- **Worktree branched before wave 1 merged.** The plan's `<read_first>` block cited line numbers in `.claude/commands/run-analyzer.md` that reflected the pre-wave-1 file state (e.g., line 67, 133, 144, 213, 215). The worktree's actual file had those references at lines 82, 170, 181, 250, 252 because the file is the post-Plan-02-03 version (with the self-audit step added). The plan's content-based replacement instructions were unambiguous, so the line-number drift did not cause any execution ambiguity. All six dereferences were applied by content match.
- **The `02-RESEARCH.md` reference on the recipe's line 162 ("verified as A6 in `02-RESEARCH.md`") was NOT dereferenced** because the plan's Group E enumerated exactly 6 dereferences and this was not in the list. The plan's grep gate is `grep -nF '.planning/' run-analyzer.md`, which does not match the bare `02-RESEARCH.md` reference on line 162 either, so the gate passes. If a future plan wants 100% self-contained framing it can fold this in; it was out of scope for Plan 03-03.

## Threat Flags

None. This plan only edits docs / recipe / config files. No new code surface, no new endpoints, no new auth paths. The `DATA_SOURCE=csv` short-circuit only triggers on the literal value `csv` (any other value, including unset, falls through to the existing `bq` probe). The cloud-routine walkthrough uses placeholder values only (`<your GCP project id>`, `<from your local .env>`, empty `NOTION_REPORT_PAGE_ID=`).

## Self-Check: PASSED

Verified post-write:

- `.planning/phases/03-csv-parity-and-operational-polish/03-03-SUMMARY.md` exists (this file).
- Task 1 commit `3ec3ddc` present in `git log`.
- Task 2 commit `acaa2f8` present.
- Task 3 commit `dc7566e` present.
- Task 4 commit `4c3a07d` present.
- `grep -nF '.planning/' .claude/commands/run-analyzer.md` returns no matches.
- `grep -nF 'Service account key' docs/schedule.md` returns no matches.
- None of the four removed env vars appear in `.env.example`.
- `head -25 CHANGELOG.md | grep -c 'Plan 03-03'` returns 5.
- No em dashes in any of the four modified files.
