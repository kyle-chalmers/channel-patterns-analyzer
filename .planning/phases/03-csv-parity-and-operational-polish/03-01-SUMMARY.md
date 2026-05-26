---
phase: 03-csv-parity-and-operational-polish
plan: 01
subsystem: csv-fallback
tags: [csv, fixtures, zoneinfo, argparse, stdlib, tech-debt]

# Dependency graph
requires:
  - phase: 01-first-notion-report-end-to-end
    provides: existing csv_fallback_loader scaffold, sample_data/ schema mirroring BigQuery tables, CHANGELOG.md per-file entry convention
  - phase: 02-honest-analyst-depth
    provides: CLAUDE.md voice gate, BUSINESS_RULES.md Phoenix-tz contract, sql/ canonical `CURRENT_DATE("America/Phoenix")` form
provides:
  - Phoenix-anchored CSV fixture generator (no system-local date leakage)
  - --snapshot-date YYYY-MM-DD override for stale-data fixture testing
  - honest requirements.txt (stdlib-only, no dangling cross-references)
  - CHANGELOG.md Plan 03-01 entry under 2026-05-25
affects: [03-02-PLAN.md csv query helper, 03-03-PLAN.md recipe CSV branch]

# Tech tracking
tech-stack:
  added: []  # no new deps; only stdlib zoneinfo + argparse
  patterns:
    - argparse + type=date.fromisoformat for safe CLI date input
    - Phoenix-tz-aware datetimes via ZoneInfo("America/Phoenix") (no manual "Z" suffix)
    - stdlib-only Python utilities (PROJECT.md "Constraints")

key-files:
  created: []
  modified:
    - scripts/csv_fallback_loader.py
    - requirements.txt
    - CHANGELOG.md

key-decisions:
  - "Replaced fake-UTC `.isoformat() + 'Z'` with Phoenix-tz-aware `datetime` (offset is `-07:00`, Phoenix has no DST). The lie about timezone is gone; downstream tooling that respects the offset will now compute correct date arithmetic."
  - "Adopted unconditional regeneration with `--snapshot-date` as the override seam (RESEARCH.md Q2 recommendation). No `--force`, no caching, no incremental update; the loader is stateless and idempotent given inputs."
  - "Kept random seeds (42 / 43 / 44) and generator function signatures untouched so fixture content is byte-identical for the same `--snapshot-date`. Determinism is load-bearing per PROJECT.md 'Constraints'."
  - "requirements.txt is comment-only by intent. The analyzer never runs `pip install -r requirements.txt`; the file documents that fact and points at PROJECT.md for the justification."

patterns-established:
  - "Phoenix-tz-aware default for any new operator-facing date arg: `args.snapshot_date or datetime.now(ZoneInfo('America/Phoenix')).date()`"
  - "argparse `type=date.fromisoformat` as the boundary check for YYYY-MM-DD CLI args (T-03-01-01 mitigation)"

requirements-completed:
  - CSV-01

# Metrics
duration: ~8min
completed: 2026-05-25
---

# Phase 03 Plan 01: CSV Fixture-Generator Phoenix-Anchoring Summary

**Generated CSV fixtures now sit on Phoenix time with real `-07:00` offsets and accept a `--snapshot-date` override for stale-data path testing; requirements.txt no longer points at files this repo has never had.**

## Performance

- **Duration:** ~8 min
- **Tasks:** 2 / 2
- **Files modified:** 3 (loader, requirements.txt, CHANGELOG.md)
- **Files created:** 0 (sample_data/*.csv is gitignored runtime output)

## Accomplishments

- Fixed `scripts/csv_fallback_loader.py:55` (fake `Z` suffix on naive datetime) and `:144-145` (`date.today()` returning operator's system-local date). Both bugs were flagged in `.planning/codebase/CONCERNS.md` and the Phase 3 RESEARCH.md "Tech Debt Scope Decision" table.
- Added `--snapshot-date YYYY-MM-DD` CLI arg (argparse, `type=date.fromisoformat`) that Plans 03-02 and 03-03 depend on for stale-data fixture generation.
- Removed `requirements-csv.txt` / `requirements-bigquery.txt` cross-references that have never resolved to real files in this repo. Replaced with a stdlib-only comment block.
- Logged both edits in `CHANGELOG.md` under `## 2026-05-25, Phase 3 Plan 03-01` with the standard per-file before/after/Impact-on-recent-reports shape.

## Task Commits

1. **Task 1: Fix csv_fallback_loader.py UTC bugs and add --snapshot-date arg**, `2dc0faa` (fix)
2. **Task 2: Fix requirements.txt cross-reference rot and add CHANGELOG entry**, `b7a6e4a` (docs)

## Files Created/Modified

- `scripts/csv_fallback_loader.py` (modified, 161 → 177 lines):
  - Added imports: `argparse`, `from zoneinfo import ZoneInfo`
  - `generate_video_metadata`: replaced `(datetime.combine(snapshot, datetime.min.time()) - timedelta(days=days_ago)).isoformat() + "Z"` with a Phoenix-tz-aware construction. Computed `snapshot_midnight = datetime.combine(snapshot, datetime.min.time(), tzinfo=ZoneInfo("America/Phoenix"))` once outside the loop; each row's `published_at` is `(snapshot_midnight - timedelta(days=days_ago)).isoformat()` (no manual `"Z"` suffix; output ends in `-07:00`).
  - Added `parse_args()` helper exposing one optional `--snapshot-date` flag with `type=date.fromisoformat` and `default=None`.
  - `main()`: first line is `args = parse_args()`. Snapshot selection: `args.snapshot_date or datetime.now(ZoneInfo("America/Phoenix")).date()`. Existing `print(f"Generating sample data for snapshot_date = {snapshot}")` retained.
  - Untouched: `SAMPLE_VIDEOS` tuple, random seeds (`Random(42)`, `Random(43)`, `Random(44)`), `_write` helper, all generator functions other than `generate_video_metadata`.
- `requirements.txt` (modified, 19 → 12 lines, comment-only):
  - New content states stdlib-only (`csv`, `json`, `argparse`, `datetime`, `zoneinfo`, `pathlib`, `random`) and cites PROJECT.md section "Constraints" for the no-new-deps rule.
  - External CLI tooling block names `bq` / `gcloud` (Google Cloud SDK) and `git` / `jq` as out-of-manifest dependencies.
  - Closing comment instructs future contributors to update `CHANGELOG.md` when adding any real Python dep.
- `CHANGELOG.md` (modified, +13 lines):
  - New H2-dated section `## 2026-05-25, Phase 3 Plan 03-01` inserted between the existing top divider and `## 2026-05-25` (Phase 2 Plan 02-01 entry).
  - One framing sentence: "Phase 3 Plan 03-01 fixes two date-handling bugs in the CSV fixture generator and corrects cross-reference rot in the Python dependency manifest. No analyzer behavior changes; CSV mode is not yet wired into the recipe (that lands in Plan 03-03)."
  - Two file bullets (`scripts/csv_fallback_loader.py`, `requirements.txt`), each with before / after / Impact on recent reports clauses, plus a forward-looking note on the loader.

## Verification Run

Plan-level `<verification>` block executed against the committed code:

| Check | Command | Result |
|---|---|---|
| Default Phoenix anchor | `python3 scripts/csv_fallback_loader.py` then `grep -cE '-07:00,' sample_data/video_metadata.csv` | 16 rows (= `len(SAMPLE_VIDEOS)`), all carry `-07:00` |
| `--snapshot-date` override | `python3 scripts/csv_fallback_loader.py --snapshot-date 2026-05-01` then `awk -F, 'NR>1 {print $NF}' sample_data/video_metadata.csv \| sort -u` | exactly `2026-05-01` |
| Invalid date rejected | `python3 scripts/csv_fallback_loader.py --snapshot-date not-a-date` | argparse error, exit code 2 |
| New CHANGELOG H2 | `head -10 CHANGELOG.md \| grep -E '^## 2026-'` | `## 2026-05-25, Phase 3 Plan 03-01` |
| requirements.txt comment-only | `grep -E '^[a-zA-Z]' requirements.txt \| grep -v '^#' \| wc -l` | 0 |
| Loader syntactically valid | `python3 -c "import ast; ast.parse(open('scripts/csv_fallback_loader.py').read())"` | exit 0 |
| Loader length budget | `wc -l scripts/csv_fallback_loader.py` | 177 (< 200 budget) |
| No `date.today()` left | `grep -c 'date.today()' scripts/csv_fallback_loader.py` | 0 |
| No `.isoformat() + "Z"` left | `grep -cnE '\.isoformat\(\) \+ "Z"' scripts/csv_fallback_loader.py` | 0 |
| ZoneInfo Phoenix usage | `grep -cnE 'ZoneInfo\("America/Phoenix"\)' scripts/csv_fallback_loader.py` | 2 (in `generate_video_metadata` and `main`) |
| add_argument boundary check | `grep -nE 'add_argument\("--snapshot-date".*type=date\.fromisoformat' scripts/csv_fallback_loader.py` | 1 match |

## Deviations from Plan

**1. [Rule 1, Bug: plan text vs plan acceptance gate]: requirements.txt em-dash conflict**
- **Found during:** Task 2.
- **Issue:** The plan's `<action>` block provides literal target content for `requirements.txt` that includes U+2014 characters in three places (the heading, the framing sentence, and two of the bulleted external-tool callouts). The same task's `<verify>` and `<acceptance_criteria>` then assert `! grep -nE '<em-dash>|<en-dash>' requirements.txt CHANGELOG.md` returns nothing, and `CLAUDE.md § "Voice"` (which the plan explicitly says applies) forbids em dashes. The plan's literal example text would fail the plan's own acceptance gate and violate the project-wide voice rule.
- **Fix:** Wrote the `requirements.txt` comment block with equivalent meaning but no em dashes. The heading became "Channel Patterns Analyzer Python dependencies." (period instead of em-dash splice). The two list items now use periods instead of em-dash continuations. The "stdlib only, no `pip install -r requirements.txt`" phrasing in the framing sentence is rendered as a sentence: "The analyzer itself uses only Python stdlib (...). There is no `pip install -r requirements.txt` step in the operator workflow."
- **Rationale:** `CLAUDE.md` voice rule wins over the plan's literal example (deviation rule precedence: CLAUDE.md directives take priority). The plan's intent is "honest stdlib-only manifest, no dangling refs" and that is preserved verbatim; only punctuation changed.
- **Files modified:** `requirements.txt`.
- **Commit:** `b7a6e4a`.

**2. [Rule 1, Bug: acceptance regex vs reasonable formatting]: `add_argument` single-line consolidation**
- **Found during:** Task 1 verification pass.
- **Issue:** Initial implementation used a multi-line `parser.add_argument(\n    "--snapshot-date",\n    type=date.fromisoformat,\n    ...)` form that is more readable. Acceptance criterion regex is `grep -nE 'add_argument\("--snapshot-date"'` which requires the arg name to sit on the same line as `add_argument(`.
- **Fix:** Consolidated to `parser.add_argument("--snapshot-date", type=date.fromisoformat, default=None, help=(...))` on one logical line so the regex matches.
- **Files modified:** `scripts/csv_fallback_loader.py`.
- **Commit:** `2dc0faa` (final form; intermediate multi-line draft was never committed).

**No architectural changes (Rule 4) required.**

## Threat Surface Scan

Plan's `<threat_model>` covered: CLI arg input boundary (mitigated via argparse `type=date.fromisoformat`), fixture file disclosure (accept; `sample_data/` is gitignored), timezone metadata correctness (mitigated by replacing fake-`Z` with real offset), supply chain (N/A; no new packages).

No new security-relevant surface introduced beyond what the plan anticipated. No threat flags raised.

## Known Stubs

None. The loader fully writes Phoenix-anchored CSVs and the `--snapshot-date` arg is fully wired; nothing is mocked or deferred. CSV-mode end-to-end runnability through the recipe arrives in Plan 03-03; this plan is the loader-only slice and is complete in scope.

## Notes for Plan 03-02 and Plan 03-03

- The loader now generates fixtures with `published_at` ending in `-07:00`. Any downstream code that parses `published_at` from the CSV must use `datetime.fromisoformat()` (Python 3.11+) which handles the offset natively, NOT a `strip("Z")`-then-parse pattern.
- `--snapshot-date 2026-05-01` (or any past date) is the canonical way to exercise the stale-data branch in the recipe's data-health step. Pair with a runbook test that asserts the analyzer emits the stale-table flag.
- `sample_data/` is gitignored. Re-run the loader before running the analyzer in CSV mode.

## Self-Check: PASSED

- Files exist:
  - FOUND: `scripts/csv_fallback_loader.py`
  - FOUND: `requirements.txt`
  - FOUND: `CHANGELOG.md`
- Commits exist (on branch `worktree-agent-af4cad5f61851c292`):
  - FOUND: `2dc0faa` (Task 1)
  - FOUND: `b7a6e4a` (Task 2)
- Plan verification block: all 5 numbered checks pass (see "Verification Run" table above).
- Plan success criteria: all 6 satisfied.
