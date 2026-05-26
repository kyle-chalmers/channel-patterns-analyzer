---
phase: 01-first-notion-report-end-to-end
reviewed: 2026-05-25T12:00:00-07:00
depth: standard
files_reviewed: 9
files_reviewed_list:
  - .claude/commands/run-analyzer.md
  - .claude/skills/write-notion-report/SKILL.md
  - .gitignore
  - CHANGELOG.md
  - docs/runbook.md
  - runs/README.md
  - sql/02_top_full_length_videos.sql
  - sql/03_age_controlled_performance.sql
  - sql/04_data_health_check.sql
findings:
  critical: 2
  warning: 7
  info: 5
  total: 14
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-05-25T12:00:00-07:00
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 1 ships the SQL pulls, the Notion-writing Skill, the `/run-analyzer` recipe, and the supporting docs/runtime schema. The pieces fit together at a high level and the recipe's contract with the Skill is mostly coherent, but adversarial reading surfaces two correctness issues that will produce wrong outputs on any run that exercises them, plus several internal-consistency gaps between the recipe, the Skill, and the runs schema. Highlights:

- `BLOCKER`: `runs/README.md` still documents the legacy query filenames (`01_data_health.sql`, `02_top_videos.sql`, `03_age_controlled.sql`, `04_traffic_sources.sql`) while the recipe writes the actual files under different names (`data_health.json`, `top_full_length_videos.json`, `eligible_video_count.json`). The two contracts no longer agree; any tooling that reads the schema doc will look in the wrong place.
- `BLOCKER`: The recipe's Step 1 transport probe says "Else check whether `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly` is loaded in the session," but never specifies how to perform that check, and the smoke-test note instructs operators to drive the choice with `BQ_TRANSPORT` env var which the recipe itself never reads. Operators following the recipe verbatim cannot deterministically force the `bq_mcp` branch, which is the exact branch Phase 1 said it could not verify end-to-end.
- Several WARNING-level inconsistencies between recipe, Skill, runbook, and runs/README schema (operator-message strings, error categories, summary.json field set drift).
- One SQL correctness gap in the `eligible_video_count` inline query (it cannot tolerate `daily_video_stats` being empty even though the recipe's NULL-guard prose claims it does).

No security vulnerabilities or hardcoded secrets. Voice violations in the documentation prose itself are tracked as Info since they do not affect runtime correctness, but the recipe authors might want to know.

## Critical Issues

### CR-01: `runs/README.md` schema example uses stale query filenames that no longer match what the recipe writes

**File:** `runs/README.md:9-15, 49-52`
**Issue:** The folder layout block at the top of `runs/README.md` lists the queries dir as containing `01_data_health.json`, `02_top_videos.json`, `03_age_controlled.json`, `04_traffic_sources.json`. The schema example a few lines down lists `01_data_health.sql` and `02_top_videos.sql` in `queries_run`. But the recipe (`.claude/commands/run-analyzer.md` Step 2, Step 3, Step 5) writes:

- `runs/{run_date}/queries/data_health.json` (no `04_` prefix; despite reading from `sql/04_data_health_check.sql`)
- `runs/{run_date}/queries/top_full_length_videos.json` (no `02_` prefix)
- `runs/{run_date}/queries/eligible_video_count.json` (a new file the README doesn't mention at all)

Confirmed by the working tree status: `runs/2026-05-25/queries/data_health.json`, `top_full_length_videos.json` exist; no `01_data_health.json` exists. The schema doc is the contract for `summary.json`; an auditor or downstream tool that reads README first will look in the wrong place and assume runs are broken.

The `03_age_controlled.json` and `04_traffic_sources.json` listings are even more misleading: Phase 1 doesn't run an age-controlled query at all (sql/03 is staged for Phase 2) and never runs a traffic-sources query (sql/05 does not exist in this repo).

**Fix:** Update `runs/README.md` to match what the recipe actually writes:

```
runs/
  2026-05-25/
    summary.json
    queries/
      data_health.json
      top_full_length_videos.json
      eligible_video_count.json   # Phase 2 / 02-02
    report.md
```

And update the `queries_run` example in the JSON schema block to reference the actual `sql/04_data_health_check.sql` and `sql/02_top_full_length_videos.sql` paths (or use the bare query name without the SQL file's `NN_` prefix, since `queries_run[].file` is documented as the SQL file, not the JSON output file). Pick one convention and apply it.

### CR-02: Step 5 inline SQL claims a NULL-guard that doesn't actually short-circuit when `daily_video_stats` is empty

**File:** `.claude/commands/run-analyzer.md:122-143`
**Issue:** The inline SQL in Step 5 uses `LEAST(MAX(video_metadata.snapshot_date), MAX(daily_video_stats.snapshot_date))` as `latest_common`. The doc comment immediately below claims:

> If either `video_metadata` or `daily_video_stats` is empty, `LEAST(NULL, X)` returns NULL, which would silently produce `eligible_count = 0` and a 0 denominator for confidence labels (CR-02). The Step 2 data-health check is the primary STOP for empty source tables; these guards are defense-in-depth at the SQL layer.

Tracing the actual SQL: the outer `WHERE (SELECT snapshot_date FROM latest_common) IS NOT NULL AND m.snapshot_date = (...) AND m.video_type = 'full_length' AND DATE_DIFF(...) >= 14` does block all rows when `latest_common.snapshot_date` is NULL — so far so good. BUT the inner `total_full_length` subquery (line 131-134) only checks `IS NOT NULL` and `m2.snapshot_date = (...)`; it omits the `DATE_DIFF >= 14` filter (correctly, since that's the point of `total_full_length`), so it returns 0 cleanly. The query returns `(eligible_count=0, total_full_length=0, latest_common_snapshot=NULL)`.

The recipe's Step 5 documentation says this `eligible_count=0` outcome is handled by Step 2 (which STOPS on empty source tables). But Step 2 only stops on the four data-health tables being missing or returning zero rows from the `MAX(snapshot_date)` query — and `MAX(snapshot_date) FROM <empty_table>` returns one row with NULL, not zero rows. So the Step 2 empty-result guard does NOT fire on a genuinely empty `daily_video_stats`. The Step 5 query then silently returns `eligible_count = 0`, the Step 6 confidence-label code sees `n=0` and (per the table) tags every claim `low confidence`. The downstream report is wrong: it claims `low confidence (small sample), n=0` for every channel-wide claim, instead of stopping or surfacing a structural failure.

This is a contract violation against `BUSINESS_RULES.md § 3` ("If a required table is missing or empty... Do not silently produce a report") and against `CLAUDE.md § "When something blocks the run"` ("If a required table is missing or empty, stop and report it").

**Fix:** Either (a) tighten Step 2 to fail when any of the four data-health rows has `latest_snapshot IS NULL` (treat it as `empty_result`), or (b) add an explicit Step 5 check: if `eligible_count == 0` AND `latest_common_snapshot IS NULL`, route to the `empty_result` failure path with `step: "eligible_count"` and STOP. Option (a) is cheaper and matches the recipe's existing failure-routing logic.

Suggested Step 2 patch:

```
- If any row has latest_snapshot IS NULL, record errors: [{"category": "empty_result", "message": "<table_name> has no rows (latest_snapshot is NULL)", "step": "data_health"}]. Operator message names docs/runbook.md section "Required table is missing or empty". STOP.
```

## Warnings

### WR-01: Transport probe for `bq_mcp` is unimplementable as written

**File:** `.claude/commands/run-analyzer.md:26-30, 38`
**Issue:** Step 1 says "check whether `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly` is loaded in the session. If yes, set `TRANSPORT=bq_mcp`." There is no mechanism described for performing that check. The recipe's later smoke-test note tells operators to run the recipe once with `BQ_TRANSPORT=bq_cli` and once with `BQ_TRANSPORT=bq_mcp` to exercise both branches, but the recipe never reads `BQ_TRANSPORT` — Step 1 deterministically falls into `bq_cli` whenever `command -v bq` succeeds, which it almost always will on Kyle's laptop.

Net effect: the `bq_mcp` branch is unreachable in normal operation and there's no operator-controllable override. This is the exact "MCP branch documented but unverified end-to-end" gap the smoke-test note acknowledges, and the recipe doesn't actually provide the override hook.

**Fix:** Add an explicit env-var override at the top of Step 1:

```
0. If `BQ_TRANSPORT` is set to `bq_cli` or `bq_mcp`, use it verbatim and skip auto-detection. If set to any other value, record `warnings: ["bq_transport_invalid: <value>; falling back to auto-detect"]` and continue with the auto-detect probe.
```

And specify the actual detection method for `bq_mcp` (e.g., "the agent can introspect available tools at session start; if the tool name appears in that list, the transport is available"). Without this, smoke-testing the MCP branch is impossible.

### WR-02: Recipe Step 9 references "skill_unavailable" category but the Skill's canonical category list doesn't include it

**File:** `.claude/commands/run-analyzer.md:351` and `.claude/skills/write-notion-report/SKILL.md:160-169`
**Issue:** Step 9 says: "If the Skill is not loaded in the session (the `.claude/skills/write-notion-report/SKILL.md` file is missing or the runtime did not pick it up), treat as `{"ok": false, "category": "skill_unavailable"}`." But the Skill's documented category enum (`input_invalid | env_missing | parent_not_found | permission_denied | transport_error | unknown`) does not contain `skill_unavailable`. The mapping table also explicitly maps "MCP tool not loaded in session" to `transport_error`, not `skill_unavailable`.

This creates two problems:
1. `summary.json.errors[].category` ends up with a value that doesn't appear in any runbook section, breaking the recipe's own claim ("the runbook's section headings map one-to-one to these strings, so an operator looking at `summary.json.errors[].category` can find the right recovery section").
2. The Step 11 operator-message NOTION-FAIL pattern injects `{category}` directly into the message, surfacing a category to the operator that contradicts the canonical list documented in the Skill.

**Fix:** Either add `skill_unavailable` to the Skill's category enum (and a corresponding runbook subsection), or change Step 9 to record `category: "transport_error"` with `message: "write-notion-report skill not loaded in session"` for consistency with the mapping table.

### WR-03: Recipe-vs-runbook drift on the `NOTION-FAIL` operator message section name

**File:** `.claude/commands/run-analyzer.md:383-386` and `docs/runbook.md:65`
**Issue:** Step 11 NOTION-FAIL message: `Recovery: see docs/runbook.md § 'Notion write failed'`. The runbook section is titled `## Notion write failed` (line 65) — exact match. Good. But the BQ-FAIL section name is left as `{relevant section}` and the recipe gives three candidates: "BigQuery auth failure", "Required table is missing or empty", "A required table is stale". The runbook has the first two verbatim (lines 9, 41) but the third runbook section is titled "A required table is stale" (line 29), which matches. So far so good.

Issue: the recipe's Step 2 `bq_auth` failure routing on line 63 says "Operator message names docs/runbook.md section 'BigQuery auth failure'" — that is the runbook section title verbatim. Step 2's `missing_table` routing on line 64 names "Required table is missing or empty" — also verbatim. Step 2's `empty_result` routing on line 65 also names "Required table is missing or empty". Step 3's BQ-03 empty routing on line 75 names the same section.

However, the recipe never wires the `bq_stale` category at all. If a table is stale (per BUSINESS_RULES.md §3), the recipe handles it inline (Step 2 builds `stale_tables` and downstream sections disclaim), but no error is recorded and no operator message points to the "A required table is stale" runbook section. The three BQ-FAIL operator message section candidates list "A required table is stale" as a valid choice, but no code path actually emits it. Dead branch.

**Fix:** Either remove "A required table is stale" from the BQ-FAIL section candidate list (since stale tables don't fail the run) or document that staleness is surfaced via the report's Data Health section rather than the operator message, and explicitly say the BQ-FAIL pattern only fires for `bq_auth`, `missing_table`, and `empty_result`.

### WR-04: `voice_audit` is required in summary.json but `runs/README.md` example doesn't list it as required, and the schema is documented inconsistently

**File:** `runs/README.md:32-91` and `.claude/commands/run-analyzer.md:368, 323`
**Issue:** The recipe (Step 10, line 368) says `voice_audit` MUST be present whenever Step 7 ran, AND the recipe (line 323) says "A missing or empty `summary.json.voice_audit` block after a successful run indicates the self-audit step did not execute. That is visible after the fact even though enforcement is markdown, not code; it is itself a finding for the next run's analyst to investigate."

But `runs/README.md` line 91 frames this as "a finding for next-run analysts to investigate" — soft enforcement only. There's no hard schema gate. Worse, the `voice_audit.checks_passed` list in the README example (lines 59-69) shows only 10 of the 17 canonical check identifiers from the recipe (Step 7, lines 295-311). The 7 missing identifiers in the README example are: `cross_age_window_labeled`, `trending_claims_have_minimum_age`, `confidence_n_matches_comparison_set`, `confidence_thresholds_correct`, `no_en_dashes_as_punctuation`, `multi_week_claims_self_contained`, `numbers_match_underlying_query_results`.

The README explicitly says "The full set lives in the recipe and should be re-derived from there, not duplicated here" (line 88), but then shows a partial duplication anyway, which is the worst of both worlds: it looks authoritative without being authoritative.

**Fix:** Either replace the README's `checks_passed` example with `["<see recipe Step 7 for the 17 canonical identifiers>"]` and a one-line note, OR include all 17 identifiers in the example so the doc agrees with the recipe. Don't half-list.

### WR-05: Empty `What is working` rendering rule conflicts between Skill and recipe

**File:** `.claude/skills/write-notion-report/SKILL.md:93, 109` and `.claude/commands/run-analyzer.md:202`
**Issue:** The Skill says: "If the section is empty in Phase 1, the placeholder text from `markdown_body` ('Not analyzed in this run, see Phase 2 for the full analytical pass') renders as a single `paragraph`." But the recipe's Step 6 (rewritten by Plan 02-02) now produces all six sections every run with real findings or with the explicit `Nothing material to report this week.` line (recipe line 208-210). The "Not analyzed in this run, see Phase 2" placeholder no longer matches what the recipe writes; it's a Phase 1 vestige in the Skill doc that contradicts the Phase 2 recipe.

If the Skill is updated next to enforce its documented placeholder against the actual `markdown_body`, it will reject perfectly valid drafts.

**Fix:** Drop the Phase-1-placeholder language from the Skill's per-section table (lines 93-96). Replace with: "The Skill renders whatever `markdown_body` contains for the section, including the explicit `Nothing material to report this week.` line or the D-12 stale-table disclaimer line from the recipe."

### WR-06: `.gitignore` negation pattern relies on git directory-traversal semantics that need documentation

**File:** `.gitignore:43-48`
**Issue:** The `.gitignore` correctly uses `.claude/skills/*` (not `.claude/skills/`) so the negation `!.claude/skills/write-notion-report/` works. The inline comment explains this. Good. But the `**` form on line 48 (`!.claude/skills/write-notion-report/**`) is double-defensive and worth checking: if git's interpretation of `!.../write-notion-report/` already re-includes everything under it, the `**` line is redundant; if it doesn't, then this idiom is doing real work. The empirical 2026-05-25 verification cited in the comment is the right move, but no one else can re-verify this without re-running the empirical test.

Adversarial concern: if a future operator deletes the `**` line thinking it's redundant, the entire skill body might get re-ignored silently. The comment doesn't explicitly warn against the deletion.

**Fix:** Extend the comment block:

```
# The `**` negation on the next line is REQUIRED. Re-including a directory
# (`!<dir>/`) does not automatically re-include the files inside it under all
# git versions. Verified empirically 2026-05-25 against git 2.x — do not
# remove without re-testing.
```

### WR-07: `eligible_count` SQL applies the 14-day filter against `published_at` cast to DATE, but `published_at` semantics are not pinned

**File:** `.claude/commands/run-analyzer.md:140` and `sql/02_top_full_length_videos.sql:44`, `sql/03_age_controlled_performance.sql:45,55`
**Issue:** Every age computation does `DATE_DIFF(CURRENT_DATE("America/Phoenix"), DATE(m.published_at), DAY)`. `published_at` is presumably a `TIMESTAMP` from the YouTube API (UTC). The `DATE()` cast strips the time component AND the timezone, so a video published 2026-05-25 04:30 UTC becomes `DATE 2026-05-25`, but the same instant is `2026-05-24 21:30` Phoenix-local — so a video that's been live "yesterday" in Phoenix time gets `days_since_published = 0` (the same Phoenix calendar day), not 1. The opposite edge case: a video published at 2026-05-25 00:30 Phoenix (07:30 UTC) gets cast to `DATE 2026-05-25` UTC, then compared to Phoenix-today, and on Phoenix midnight rollover the days_since values can swing by 1 in a way that's not obviously correct.

This will produce edge-case off-by-one errors in the 14-day cutoff for videos near the boundary. For a channel publishing ~1 video/week the effect is small, but for the `days_since_published < 14` exclusion rule it's the difference between including and excluding a borderline video in `eligible_count`.

**Fix:** Cast through Phoenix:

```sql
DATE_DIFF(CURRENT_DATE("America/Phoenix"), DATE(m.published_at, "America/Phoenix"), DAY)
```

(BigQuery's `DATE(TIMESTAMP, timezone)` two-arg form converts the timestamp to the named tz before truncating.) Same fix needed in `sql/02`, `sql/03`, and the recipe's inline Step 5 SQL.

## Info

### IN-01: `sql/02_top_full_length_videos.sql` header references `sql/01_latest_snapshot_overview.sql` which does not exist in this repo

**File:** `sql/03_age_controlled_performance.sql:8` and `sql/04_data_health_check.sql:8`
**Issue:** Both files have a header comment "Dataset name: bare `youtube_analytics.<table>` form; replace if your dataset has a different name (see header of sql/01_latest_snapshot_overview.sql)." There is no `sql/01_latest_snapshot_overview.sql` in the repo (`ls sql/` shows only `02`, `03`, `04`). Dangling reference.

**Fix:** Either restore `sql/01_latest_snapshot_overview.sql` or replace the comment with self-contained dataset-replacement guidance.

### IN-02: Recipe Step 4 same-day-retry filename pattern is regex-incomplete

**File:** `.claude/commands/run-analyzer.md:85, 95`
**Issue:** The grep pattern `'^[0-9]{4}-[0-9]{2}-[0-9]{2}(-[0-9]+)?\.md$'` accepts `2026-05-25-N.md` where N is one or more digits. Fine. But `sort -V` (version sort) on `2026-05-25.md`, `2026-05-25-1.md`, `2026-05-25-2.md` orders them: `2026-05-25-1.md`, `2026-05-25-2.md`, `2026-05-25.md`. Note `2026-05-25.md` sorts LAST under `sort -V`. So `tail -n 1` returns the un-suffixed file. If a same-day retry created `2026-05-25-1.md`, the canonical-file selection returns `2026-05-25.md` (the original) not `2026-05-25-1.md` (the retry). That contradicts the comment "latest same-day retry wins as the canonical record for that date."

**Fix:** Either rename retries with a leading numeric suffix so version-sort works correctly, or do an explicit two-pass selection: prefer the highest-numbered `-N.md` if any exist, else fall back to the un-suffixed file. A safer one-liner: `ls reports/ | grep -E "^${d}(-[0-9]+)?\.md$" | awk -F'-' '{print NF, $0}' | sort -n | tail -n 1 | cut -d' ' -f2-`.

### IN-03: `CHANGELOG.md` violates the project's own voice rules

**File:** `CHANGELOG.md:13, 14, 16, 18`
**Issue:** Several entries use em dashes (`—` U+2014): line 13 ("changed: before — joined…"), line 14 ("same three changes…"), line 16 ("Plan 02-02 extends the recipe"), line 18 ("for each passed check…"). The project's voice rule (CLAUDE.md § "Voice") forbids em dashes. Granted, CHANGELOG entries aren't published Notion reports, but the voice rule is documented as project-wide and the same review tooling the recipe enforces on reports doesn't run against CHANGELOG.

**Fix:** Optional — replace em dashes with commas, periods, or parentheses in CHANGELOG entries, OR document an explicit exception (e.g., "voice rules apply to published Notion reports and report drafts only; internal docs are exempt").

### IN-04: `runs/README.md` schema example contains a fictitious `notion_url` format

**File:** `runs/README.md:56`
**Issue:** The example shows `"notion_url": "https://www.notion.so/Weekly-report-2026-05-24-<shortid>"`. Real Notion page URLs are typically `https://www.notion.so/<workspace>/<title-with-dashes>-<32-char-id>`. An operator copying the example into a smoke-test fixture will get a URL pattern that doesn't match production. Low impact since it's just an example, but worth pinning.

**Fix:** Replace with `"https://www.notion.so/<workspace-or-page-slug>/Weekly-report-2026-05-24-<32-char-id-no-dashes>"` or use a clearly-fake placeholder like `"<notion url returned by the Skill>"`.

### IN-05: The Skill's input contract allows empty `headline` only when `data_health.stale_tables` is non-empty, but the recipe never enforces this constraint at the Step 8 dict-assembly step

**File:** `.claude/skills/write-notion-report/SKILL.md:21` and `.claude/commands/run-analyzer.md:330-338`
**Issue:** The Skill input contract: "`headline` ... Empty string is allowed only when `data_health.stale_tables` is non-empty and the headline is essentially 'data is stale'." The recipe's Step 8 validation only checks for key presence ("if any key is missing"), not the contextual rule. If the analyzer produces an empty headline for any other reason (model omitted the section, prose parser failed), Step 8 passes and the Skill receives an empty string. The Skill's documented Validation order item 5 (`markdown_body` is non-empty string) doesn't reject empty `headline` explicitly — only `markdown_body` non-empty is checked.

So an empty headline silently ships an empty `paragraph` block under the Headline heading.

**Fix:** Either tighten the Skill validation to enforce the conditional rule (`if headline == "" and len(data_health.stale_tables) == 0: return input_invalid`), or remove the conditional carve-out from the contract and require `headline` to always be non-empty.

---

_Reviewed: 2026-05-25T12:00:00-07:00_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
