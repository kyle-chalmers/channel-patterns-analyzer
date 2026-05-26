---
phase: 01-first-notion-report-end-to-end
fixed_at: 2026-05-25T13:30:00-07:00
review_path: .planning/phases/01-first-notion-report-end-to-end/01-REVIEW.md
iteration: 1
findings_in_scope: 14
fixed: 12
skipped: 2
status: partial
---

# Phase 1: Code Review Fix Report

**Fixed at:** 2026-05-25T13:30:00-07:00
**Source review:** `.planning/phases/01-first-notion-report-end-to-end/01-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 14 (2 critical, 7 warning, 5 info; `fix_scope: all`)
- Fixed: 12
- Skipped: 2 (both Info; reviewer's stated context did not match the current code)

## Fixed Issues

### CR-01: `runs/README.md` schema example uses stale query filenames

**Files modified:** `runs/README.md`
**Commit:** `ece374d`
**Applied fix:** Replaced the folder layout block to list the actual files the recipe writes (`data_health.json`, `top_full_length_videos.json`, `eligible_video_count.json`) with one-line annotations naming the source SQL. Updated the `queries_run` JSON example to reference the real SQL paths (`sql/04_data_health_check.sql`, `sql/02_top_full_length_videos.sql`) plus the recipe-inline eligible-count entry.

### CR-02: Step 5 inline SQL claims a NULL-guard that doesn't short-circuit when source tables are empty

**Files modified:** `.claude/commands/run-analyzer.md`
**Commit:** `ec6e0b6`
**Applied fix:** Added a new bullet to Step 2's failure routing: if any row of the `sql/04` result has `latest_snapshot IS NULL`, record an `empty_result` error and STOP. This closes the gap the reviewer identified, where `MAX(snapshot_date) FROM <empty_table>` returns one NULL row (so the existing zero-rows check does not fire), and the Step 5 `LEAST(NULL, X)` would otherwise silently produce `eligible_count = 0`. The fix is option (a) from the reviewer's two suggestions (Step-2-side tightening rather than a Step-5-side check), since it stops the run earlier and reuses the existing failure-routing path.

### WR-01: Transport probe for `bq_mcp` is unimplementable as written

**Files modified:** `.claude/commands/run-analyzer.md`
**Commit:** `08811f9`
**Applied fix:** Added an explicit `BQ_TRANSPORT` operator-override block at the top of Step 1 (before auto-detect): if set to `bq_cli` or `bq_mcp`, use verbatim and skip the probe; if set to any other value, record a `bq_transport_invalid` warning and fall back to auto-detect. Specified the actual detection method for the `bq_mcp` branch (agent's session-tool introspection at session start, not a shell command). This makes the smoke-test note at the bottom of Step 1 actually executable.

### WR-02: Recipe Step 9 references `skill_unavailable` category not in the Skill's enum

**Files modified:** `.claude/commands/run-analyzer.md`
**Commit:** `56213a6`
**Applied fix:** Took option (b) from the reviewer (the cheaper option): changed Step 9 to record `category: "transport_error"` with `message: "write-notion-report skill not loaded in session"` when the Skill is unavailable, matching the Skill's own mapping table for "MCP tool not loaded in this session". Now `summary.json.errors[].category` maps 1:1 to a runbook section.

### WR-03: Recipe-vs-runbook drift on the `NOTION-FAIL` operator message section name

**Files modified:** `.claude/commands/run-analyzer.md`
**Commit:** `3a84120`
**Applied fix:** Removed "A required table is stale" from the BQ-FAIL section candidate list in Step 11, since no code path actually emits a stale-table failure. Documented explicitly that stale tables are surfaced inline in the report's Data Health section (D-12) and never route through the BQ-FAIL operator message. Also pinned which error categories map to which runbook section (`bq_auth` -> "BigQuery auth failure"; `missing_table`/`empty_result` -> "Required table is missing or empty").

### WR-04: `voice_audit` schema documented inconsistently between recipe and `runs/README.md`

**Files modified:** `runs/README.md`
**Commit:** `d32f1f6`
**Applied fix:** Replaced the partial 10-identifier `checks_passed` example with the full 17-identifier set, in the same order the recipe documents them. Updated the accompanying prose paragraph to enumerate the full list explicitly while still naming the recipe as the source of truth.

### WR-05: Empty `What is working` rendering rule conflicts between Skill and recipe

**Files modified:** `.claude/skills/write-notion-report/SKILL.md`
**Commit:** `e2a62bb`
**Applied fix:** Dropped the Phase-1-only placeholder language (`"Not analyzed in this run, see Phase 2..."`) from the per-section block mapping table. Replaced with a description that the Skill renders whatever `markdown_body` contains, including the recipe's two explicit empty-state lines (`Nothing material to report this week.` or the D-12 stale-table disclaimer). Also reworded the follow-up paragraph that previously enforced "the placeholder paragraph already present in `markdown_body`" so future Skill edits don't reject perfectly valid Phase-2 drafts.

### WR-06: `.gitignore` `**` negation deserves a stronger warning against deletion

**Files modified:** `.gitignore`
**Commit:** `579a320`
**Applied fix:** Extended the comment block immediately above the `!.claude/skills/write-notion-report/**` line with an explicit `DO NOT DELETE` warning, the empirical reasoning (re-including a directory with `!<dir>/` does not automatically re-include the files under all git versions, especially when the parent `.claude/skills/*` pattern already matched the children), and a re-verification recipe (touch a file under the skill dir, `git check-ignore -v` on it). Also removed a stray em dash from a pre-existing comment in the same block for voice-rule consistency.

### WR-07: `eligible_count` SQL applies the 14-day filter against `published_at` cast to DATE without a timezone

**Files modified:** `sql/02_top_full_length_videos.sql`, `sql/03_age_controlled_performance.sql`, `.claude/commands/run-analyzer.md`
**Commit:** `0836550`
**Applied fix:** Switched all three age-computation sites from `DATE(m.published_at)` (single-arg, truncates at UTC day boundary) to `DATE(m.published_at, "America/Phoenix")` (two-arg, converts to Phoenix timezone before truncating). Added a "Phoenix-tz note" paragraph immediately under the recipe's inline Step 5 SQL explaining the rationale, the off-by-one this prevents at the 14-day exclusion boundary, and that all three SQL sites now share one timezone semantic.

### IN-03: `CHANGELOG.md` violates the project's own voice rules

**Files modified:** `CHANGELOG.md`
**Commit:** `9d78c3e`
**Applied fix:** Replaced all 4 em dashes (`—` U+2014) with commas, semicolons, or sentence boundaries. The voice rule from `CLAUDE.md § "Voice"` is documented as project-wide, and the changelog is the most visible non-report doc, so fixing it (rather than carving out an exception) keeps the rule consistent across the repo.

### IN-04: `runs/README.md` schema example contains a fictitious `notion_url` format

**Files modified:** `runs/README.md`
**Commit:** `6cada6c`
**Applied fix:** Replaced the implausible `https://www.notion.so/Weekly-report-2026-05-24-<shortid>` with a labeled placeholder that names what really fills the field (the URL returned by the Skill) and a realistic shape (`https://www.notion.so/<workspace-slug>/Weekly-report-2026-05-24-<32-char-page-id-no-dashes>`). An operator copying the example into a smoke test now gets a URL pattern that lines up with the production wrapper's actual return value.

### IN-05: Skill input contract allows empty `headline` only when stale tables are non-empty, but no validation enforces it

**Files modified:** `.claude/skills/write-notion-report/SKILL.md`
**Commit:** `6d5d8f8`
**Applied fix:** Added a new step 6 to the Skill's validation order: `headline` is a string, and an empty `headline` is only accepted when `len(data_health.stale_tables) > 0`. The mismatch case returns `input_invalid` with the message `"headline is empty and no stale tables are flagged"`. Updated the error-category table's `input_invalid` row to mention the new case. This closes the silent-publish path where a draft step that dropped the Headline section would otherwise ship an empty paragraph block.

## Skipped Issues

### IN-01: `sql/02_top_full_length_videos.sql` header references `sql/01_latest_snapshot_overview.sql` which does not exist in this repo

**File:** `sql/03_age_controlled_performance.sql:8` and `sql/04_data_health_check.sql:8`
**Reason:** skipped: code context differs from review. The reviewer claimed `sql/01_latest_snapshot_overview.sql` does not exist (`ls sql/` shows only `02`, `03`, `04`), but the file IS present in the current repo and was present in the worktree at the time of fix application (`ls sql/` returns `01_latest_snapshot_overview.sql`, `02_top_full_length_videos.sql`, `03_age_controlled_performance.sql`, `04_data_health_check.sql`). The dangling-reference claim does not apply; the cross-reference is valid.
**Original issue:** Both files have a header comment `(see header of sql/01_latest_snapshot_overview.sql)`. The reviewer asserted that file does not exist; verification in the worktree confirmed it does.

### IN-02: Recipe Step 4 same-day-retry filename pattern is regex-incomplete

**File:** `.claude/commands/run-analyzer.md:85, 95`
**Reason:** skipped: empirical claim in the review is incorrect. The reviewer asserted that `sort -V` on `2026-05-25.md`, `2026-05-25-1.md`, `2026-05-25-2.md` orders the bare `2026-05-25.md` LAST, so `tail -n 1` returns the un-suffixed file (wrong). Verified empirically (`printf "2026-05-25-1.md\n2026-05-25-2.md\n2026-05-25.md\n" | sort -V`): GNU sort puts the bare `.md` file FIRST and `-2.md` LAST, so `tail -n 1` correctly returns the highest-numbered retry. Tested with multi-digit retries too (`-1`, `-2`, `-10`); `sort -V` orders them numerically as expected. The recipe's behavior matches the intent stated in the comment ("latest same-day retry wins as the canonical record for that date").
**Original issue:** `sort -V` allegedly orders `2026-05-25.md` after `2026-05-25-1.md`. Empirical test contradicts this.

---

_Fixed: 2026-05-25T13:30:00-07:00_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
