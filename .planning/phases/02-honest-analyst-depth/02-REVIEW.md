---
phase: 02-honest-analyst-depth
reviewed: 2026-05-25T17:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - .claude/commands/run-analyzer.md
  - sql/02_top_full_length_videos.sql
  - sql/03_age_controlled_performance.sql
  - sql/04_data_health_check.sql
  - runs/README.md
findings:
  critical: 2
  warning: 7
  info: 4
  total: 13
status: issues_found
---

# Phase 02 Code Review Report

**Reviewed:** 2026-05-25T17:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 2 ships three correctness-focused SQL fixes (Phoenix tz everywhere, latest-common-snapshot CTE in joined queries, no LIMIT ceiling), three new recipe steps (prior-report read, eligible-count, self-audit), and two schema additions (`prior_reports_consulted`, `voice_audit`). The SQL changes are well-targeted and match the Phase 1 → Plan 01 pattern from sql/01.

The defects below cluster in three areas: (1) the recipe's prior-report selection logic does not actually yield "three most recent prior dates" when same-day retries exist, contradicting both the recipe prose and CLAUDE.md's calibration intent; (2) the `${BQ_DATASET}` string-substitution path has no validation, so a malformed env var could either silently produce broken SQL or open a backtick-escape injection vector; (3) several documentation inconsistencies create future-drift risk (recipe text claims sql/04 uses single-quoted Phoenix tz while the file uses double-quoted; banned-phrase `"as noted"` is too broad and will produce false positives; schema example shows 10/17 canonical identifiers).

The two CRITICAL findings are both correctness defects in the recipe semantics (CR-01: prior-report selection; CR-02: latest_common CTE silently returns zero rows on empty source tables). Neither is a security vulnerability, but both will silently produce wrong outputs in realistic scenarios that the design explicitly contemplates.

## Critical Issues

### CR-01: Step 4 "3 most recent prior reports" selection is wrong when same-day retries exist

**File:** `.claude/commands/run-analyzer.md:70-73`
**Issue:** The shell pipeline `ls reports/ | grep ... | grep -v "^${run_date}" | sort | tail -n 3` selects the last 3 files lexicographically, not the 3 most recent distinct prior dates. Same-day retries (`YYYY-MM-DD-N.md` naming convention documented in Step 4 itself) sort AFTER the original, so a prior-date with retries can monopolize the window.

Concrete failure: if `reports/` contains `2026-05-04.md`, `2026-05-11.md`, `2026-05-18.md`, `2026-05-18-1.md`, `2026-05-18-2.md` and `run_date=2026-05-25`, the pipeline returns `[2026-05-18.md, 2026-05-18-1.md, 2026-05-18-2.md]`. The analyzer reads three files all from the same prior date and never sees the two-and-three-week prior reports the calibration logic requires (CLAUDE.md "Persistent structure" rule: read the most recent 3-4 entries to calibrate).

This contradicts the recipe's own prose ("read the three most recent prior reports") and breaks the CLAUDE.md confidence-calibration intent (multi-week regression detection becomes impossible if all three windows are the same date).

**Fix:**
```bash
# Select the 3 most recent *distinct prior dates*, then read each date's
# canonical file (or its highest-suffix retry):
ls reports/ \
  | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}(-[0-9]+)?\.md$' \
  | sed -E 's/^([0-9]{4}-[0-9]{2}-[0-9]{2}).*/\1/' \
  | sort -u \
  | grep -v "^${run_date}$" \
  | tail -n 3
# Then for each selected date, read either {date}.md or the highest-suffix
# {date}-N.md (the latest retry is the canonical version of that date's report).
```

Also add an explicit assertion in Step 4 step 6: `prior_reports_consulted` must contain distinct dates only.

---

### CR-02: latest_common CTE produces silent zero-row results when either source table is empty

**File:** `sql/02_top_full_length_videos.sql:24-29`, `sql/03_age_controlled_performance.sql:27-32`, `.claude/commands/run-analyzer.md:95-100`
**Issue:** `LEAST(NULL, X)` returns NULL in BigQuery. If either `video_metadata` or `daily_video_stats` is empty (or temporarily reset during a pipeline incident), `MAX(snapshot_date)` returns NULL, the CTE returns NULL, and `WHERE m.snapshot_date = (SELECT snapshot_date FROM latest_common)` becomes `WHERE m.snapshot_date = NULL`, which never matches anything. The query returns zero rows with exit 0 — indistinguishable from "no full-length videos exist" from the analyzer's perspective.

This routing path is dangerous because:
1. Step 3's "If the query returns zero rows, this is a BQ-03 failure" path will fire, but the *real* failure category is `empty_source_table`, not `empty_result`, leading to misleading operator messages and runbook links.
2. The data-health step (Step 2) uses `sql/04` which queries each table independently and would catch an empty `video_metadata` separately, but it runs BEFORE the CTE-based queries; the analyzer is not instructed to skip Steps 3 and 5 when data_health rows show a fully-empty source table (only `days_stale > 3`).
3. The Step 5 inline eligible-count query has the same NULL-propagation bug, meaning the confidence-label denominator could silently become 0.

**Fix:** Add a NULL-guard in the CTE, or check the data-health result before running joined queries.

```sql
WITH latest_common AS (
    SELECT LEAST(
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.video_metadata`),
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.daily_video_stats`)
    ) AS snapshot_date
)
SELECT ...
WHERE (SELECT snapshot_date FROM latest_common) IS NOT NULL
  AND m.snapshot_date = (SELECT snapshot_date FROM latest_common)
  AND ...
```

Or, preferably, instrument Step 2's data-health parsing to detect a NULL `latest_snapshot` for any table and route to a new error category `empty_source_table` that STOPs before Step 3.

## Warnings

### WR-01: Recipe documentation drift on Phoenix-tz quote style

**File:** `.claude/commands/run-analyzer.md:38`
**Issue:** Step 2 says `The file already uses CURRENT_DATE('America/Phoenix') per the Phase 1 scaffold fix`. But Plan 01 explicitly switched all four `CURRENT_DATE()` calls in `sql/04` to **double-quoted** form `CURRENT_DATE("America/Phoenix")`. The recipe text now disagrees with the file it's referencing.

This is the kind of doc-drift CONCERNS.md warned about. A future reader debugging a timezone issue may try to "fix" sql/04 back to single-quoted form to match the recipe's claim.

**Fix:** Update line 38 to read `The file already uses CURRENT_DATE("America/Phoenix") per Plan 01's canonical-form switch, so no timezone substitution is needed.`

---

### WR-02: SIMULATE_STALE parser has no table-name validation

**File:** `.claude/commands/run-analyzer.md:47`
**Issue:** The recipe instructs: parse `SIMULATE_STALE` as comma-separated `table_name:days` pairs and "override the parsed `days_stale` for the named tables before computing `stale_tables`". There is no instruction to validate that `table_name` is one of the four known analytics tables (`video_metadata`, `daily_video_stats`, `daily_video_analytics`, `daily_traffic_sources`).

Failure modes:
- A typo (`SIMULATE_STALE="daily_video_analytic:89"`) silently fails to override anything — operator sees no stale flag in the report and assumes the test passed.
- A garbage value (`SIMULATE_STALE="../../etc/passwd:foo"`) is silently ignored or parsed as junk — no warning surfaced.
- A non-integer `days` (`SIMULATE_STALE="video_metadata:soon"`) has no specified behavior.

Not a true injection vulnerability (the recipe never shells out using the value), but the silent-failure mode defeats the override's purpose (testing the D-12 disclaimer rule end-to-end).

**Fix:** Add an explicit validation step inside the SIMULATE_STALE handler:
1. Each pair must match regex `^(video_metadata|daily_video_stats|daily_video_analytics|daily_traffic_sources):\d+$`.
2. If any pair fails validation, record `warnings: ["simulate_stale_invalid: <raw_value>"]` and skip the override (do not partial-apply).
3. If a `table_name` is valid but does not appear in the parsed `data_health` rows, that's a parser/SQL mismatch worth flagging.

---

### WR-03: Step 5 ${BQ_DATASET} substitution has no validation

**File:** `.claude/commands/run-analyzer.md:97-113`
**Issue:** The inline eligible-count SQL embeds `${BQ_DATASET}` inside BigQuery backtick-quoted identifiers: `` `${BQ_DATASET}.video_metadata` ``. Step 5 instructs "Substitute `${BQ_DATASET}` with `$BQ_DATASET` (in-memory; do not write the rewritten SQL to disk)" with no validation of the env-var value.

If `$BQ_DATASET` contained a backtick or BigQuery metacharacters, the resulting SQL could:
1. Parse-error noisily (best case).
2. Query an unintended dataset (e.g., `$BQ_DATASET="actual_dataset\`,\`other_dataset"` could potentially escape the backtick quoting in some shells/encodings).
3. Inject arbitrary SQL if the value flowed through some intermediate templating layer.

Same risk applies to Step 2 (`Substitute every literal youtube_analytics in the file contents with the value of $BQ_DATASET`) and Step 3 (same instruction).

Probability is low in normal operation (`.env` is operator-controlled), but the recipe should treat `BQ_DATASET` as a potentially-hostile input per defense-in-depth and per the CLAUDE.md "validate inputs" principle.

**Fix:** Add to Step 0 preflight: validate `BQ_DATASET` matches `^[A-Za-z_][A-Za-z0-9_]*$` (BigQuery identifier rules). Reject and STOP if it doesn't, with `errors: [{"category": "env_invalid", "message": "BQ_DATASET contains non-identifier characters", "step": "preflight"}]`.

---

### WR-04: Step 4 banned phrase "as noted" is too broad and will false-positive

**File:** `.claude/commands/run-analyzer.md:83`, `.claude/commands/run-analyzer.md:245`
**Issue:** Step 4 lists banned phrases for the prior-report-citation rule: `"as we said last week"`, `"as noted previously"`, `"the prior report"`, `"this continues the trend we observed"`, `"as noted"`.

`"as noted"` as a standalone substring matches legitimate prose: `"as noted in the data"`, `"as noted in the SQL header comment"`, `"as noted above"`, `"as noted by the upstream pipeline"`. None of these reference prior reports.

The self-audit `no_prior_report_citation` check (recipe line 245) inherits the same list. A draft that contains "as noted in the Patterns section" will fail this check, forcing a spurious fix.

**Fix:** Remove the bare `"as noted"` from the banned list. The fuller phrase `"as noted previously"` is already listed and is sufficiently specific. If the intent is to catch all "as noted" references to prior content, prefer regex-based detection (e.g., `\bas noted\b.*\b(previously|last week|in the prior|in last)\b`).

---

### WR-05: Self-audit gate has no enforcement; "missing voice_audit" only visible post-hoc

**File:** `.claude/commands/run-analyzer.md:283-287`
**Issue:** Step 7 says "The Skill MUST NOT be invoked while any item remains unticked" and "A missing or empty `summary.json.voice_audit` block after a successful run indicates the self-audit step did not execute. That is visible after the fact even though enforcement is markdown, not code."

The self-acknowledged gap: the gate is enforced entirely by the analyzer agent's compliance with markdown instructions. There is no programmatic check that prevents Step 9 (Skill invocation) from firing when Step 7 was skipped. The "missing voice_audit" detection is post-hoc and depends on the *next* run's analyst noticing it (recipe line 287: "it is itself a finding for the next run's analyst to investigate").

Concrete failure: if the analyzer skips Step 7 under context pressure (RESEARCH.md Pitfall 3, which the design explicitly contemplates), the Notion report publishes unaudited and the gap may go unnoticed for weeks.

This is fundamental to the markdown-only D-01 Layer 2 design choice and is documented as such. Flagging because:
1. The phrase "MUST NOT" overstates the enforcement strength.
2. The post-hoc detection mechanism puts the burden on the next run's analyst, who may also be context-pressured.

**Fix:** Either (a) downgrade the language to "SHOULD NOT" with a clear acknowledgment that enforcement is honor-system, or (b) add a Step 9 precondition that requires `voice_audit` to be present in working state before invoking the Skill (still markdown, but creates a second instruction the agent must violate to skip Step 7). Option (c): a future Python-side validator (out of scope here, but the recipe could TODO-flag the limitation).

---

### WR-06: Step 5 confidence-tier table contains documented ambiguity

**File:** `.claude/commands/run-analyzer.md:119-125`
**Issue:** The table says:
- `< 5` → low confidence
- `5 to 10` → moderate confidence
- `>= 10` → standard confidence

Both rows 2 and 3 claim n=10. The recipe immediately follows with "Boundary clarification: `n=10` → standard. The standard-tier boundary wins at exactly 10."

This is correct-by-prose-override but the table itself is wrong. Future readers (especially LLM agents drafting reports) will pattern-match to the table cells and may apply moderate at n=10 50% of the time. CLAUDE.md is the upstream source and it has the same ambiguity ("5 to 10" / "10 or more"); the project should resolve this in one place.

**Fix:** Rewrite the table with non-overlapping ranges:
| `eligible_count` | label |
|---|---|
| `< 5` (n=1, 2, 3, 4) | `low confidence` |
| `5 ≤ n < 10` (n=5, 6, 7, 8, 9) | `moderate confidence` |
| `>= 10` (n=10 or more) | `standard confidence` |

And consider raising a parallel fix to CLAUDE.md § "Small samples get hedged" so the ambiguity is resolved at the source.

---

### WR-07: Step 8 `notion_write_ok` undefined when dict validation fails

**File:** `.claude/commands/run-analyzer.md:302`, `.claude/commands/run-analyzer.md:329`
**Issue:** Step 8 says "if any key is missing, do NOT invoke the Skill ... and proceed to Step 10 to write summary.json." Step 10 then requires `notion_write_ok: boolean from Step 9`. If Step 9 was skipped because of dict-invalid, `notion_write_ok` is undefined — the recipe does not specify the value.

The Step 11 operator message paths require `notion_write_ok`-style state to pick between SUCCESS / NOTION-FAIL / BQ-FAIL. With `notion_write_ok` undefined, the message-selection logic is also undefined.

**Fix:** In Step 8, when validation fails, explicitly set `notion_write_ok = false` (and a corresponding error category like `report_dict_invalid` which is already specified). Update Step 10 schema to say `notion_write_ok: boolean from Step 9, or false if Step 9 was skipped due to dict validation failure`.

## Info

### IN-01: Pre-existing em dashes in runs/README.md violate the voice rules Phase 2 just enforced

**File:** `runs/README.md:1`, `runs/README.md:95-97`
**Issue:** The file contains 4 em dashes (`—`) on the lines `# Runs — audit trail`, `- reports/ — the human-readable archive`, `- docs/runbook.md — what to do when a run errors`, `- CHANGELOG.md — when the analyzer's behavior or rules change`.

Plan 02-03 SUMMARY explicitly noted this and flagged it as out-of-scope ("predate this plan and are outside its scope"). However, runs/README.md is a Phase 2-modified file, and Phase 2 just added a voice_audit step that explicitly bans em dashes. The contradiction is small (the voice rules technically apply to REPORT prose, not project docs per CLAUDE.md scope), but it's worth a cleanup pass since the file is open.

**Fix:** Replace each em dash with a colon, period, or comma per CLAUDE.md § "Prose & Anti-AI-Voice". E.g., `# Runs: audit trail`.

---

### IN-02: Schema example shows 10/17 canonical identifiers; future-drift trap

**File:** `runs/README.md:58-70`
**Issue:** The `voice_audit.checks_passed` example shows 10 of the 17 canonical identifiers defined in the recipe. The prose below says "The full set lives in the recipe and should be re-derived from there", which is the right call, but the partial example creates a subtle expectation that consumers will treat the 10 shown as canonical and not look further. If the recipe's identifier list changes (additions or renames), the schema example will silently drift without any failing check.

**Fix:** Either (a) inline all 17 identifiers in the example, accepting the duplication, or (b) shorten the example to 2-3 illustrative identifiers and add a stronger pointer (`# ... and 14 more; see Step 7 in .claude/commands/run-analyzer.md`).

---

### IN-03: PERSIST-03 .partial-state.json implementation lives only in Step 10

**File:** `.claude/commands/run-analyzer.md:336`
**Issue:** Step 10 documents the PERSIST-03 contract: "after each step that succeeds, append the cumulative state to `runs/{run_date}/.partial-state.json`". But no other step (0-9) actually instructs the analyzer to perform this append. The contract is described in the consumer (Step 10) but unimplemented at the producer sites.

A first-time operator running the recipe top-to-bottom will not write `.partial-state.json` at any earlier step, then Step 10 will look for it and find nothing.

**Fix:** Either (a) drop the partial-state mechanism entirely and rely on the working-memory-then-write-once model already in use, or (b) add an explicit "After this step succeeds, append `{step_n: <captured_state>}` to `runs/{run_date}/.partial-state.json`" sentence to each of Steps 1-9.

---

### IN-04: Dataset string-substitution rewrites comments too

**File:** `.claude/commands/run-analyzer.md:38, 57`, `sql/02:6-7`, `sql/03:6`, `sql/04:7`
**Issue:** "Substitute every literal `youtube_analytics` in the file contents with the value of `$BQ_DATASET`" applies to all occurrences, including the bare `youtube_analytics` in header comments like `-- Dataset name: bare \`youtube_analytics.<table>\` form; replace if your dataset has a different name`.

After substitution with `$BQ_DATASET="my_dataset"`, the comment becomes `-- Dataset name: bare \`my_dataset.<table>\` form; replace if your dataset has a different name`, which reads as nonsense (the instruction now points at the same dataset name as the substituted form). Cosmetic only; the SQL parses fine.

**Fix:** Either (a) accept the cosmetic drift (no functional impact), or (b) tighten the substitution rule to match only the backtick-quoted form: replace `` `youtube_analytics. `` with `` `$BQ_DATASET. ``.

---

_Reviewed: 2026-05-25T17:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
