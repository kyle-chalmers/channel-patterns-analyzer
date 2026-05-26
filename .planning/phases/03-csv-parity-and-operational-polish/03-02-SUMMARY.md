---
phase: 03-csv-parity-and-operational-polish
plan: 02
subsystem: csv-mode-query-engine
tags: [csv-mode, query-helper, json-shape-parity, stdlib-only, phoenix-tz]
requires:
  - scripts/csv_fallback_loader.py (Plan 03-01: writes Phoenix-tz-aware published_at)
provides:
  - scripts/csv_query.py (three named queries dispatched via argparse, JSON-array stdout)
affects:
  - Plan 03-03 (recipe wiring will invoke this helper for CSV-mode dispatch)
tech_stack:
  added: []
  patterns:
    - "stdlib-only Python script (argparse + csv.DictReader + json.dump)"
    - "ZoneInfo('America/Phoenix') for canonical analyzer 'today'"
    - "(video_id, snapshot_date) join key enforced via two-pass filter then join-on-video_id"
    - "BigQuery --format=json output-shape mirroring (top-level array, all string values)"
key_files:
  created:
    - scripts/csv_query.py
  modified:
    - CHANGELOG.md
decisions:
  - "Two-pass filter-then-join over a relational engine for the (video_id, snapshot_date) join, keeping the helper stdlib-only and side-stepping the BQ-SQL-to-DuckDB dialect translation problem."
  - "Empty-table NULL-guard surfaces as empty-string values rather than null, matching the SQL's IS NOT NULL short-circuit behavior at the recipe layer."
  - "Bullet appended under the existing '2026-05-25, Phase 3 Plan 03-01' CHANGELOG H2 (instead of opening a new same-date H2) so each calendar date heading stays singular per the plan's acceptance criterion."
metrics:
  duration_minutes: ~25
  completed_date: "2026-05-25"
  tasks_completed: 2
  files_created: 1
  files_modified: 1
  loc_added_helper: 210
---

# Phase 3 Plan 03-02: CSV-Mode Query Helper Summary

Stdlib-only CSV-mode query helper (`scripts/csv_query.py`, 210 lines) that emits `bq query --format=json`-shaped JSON arrays for the three live queries the analyzer recipe runs. The helper exists and is unit-callable; the recipe wiring lands in Plan 03-03.

## What shipped

| Artifact | State | Lines | Purpose |
|---|---|---|---|
| `scripts/csv_query.py` | NEW | 210 | argparse-dispatched helper, three named queries mirroring `sql/04`, `sql/02`, and the recipe's Step 5 inline SQL |
| `CHANGELOG.md` | modified | +3 lines | Plan 03-02 bullet appended to today's Phase 3 H2 |

## Query handlers (algorithm summary)

**`query_data_health()`**: per-table loop over `(video_metadata, daily_video_stats, daily_video_analytics, daily_traffic_sources)`. For each table, read CSV, compute `MAX(snapshot_date)` via Python `max(date.fromisoformat(...))`, compute `days_stale = (today_phoenix - latest).days`, append a dict with all-string values. Empty-table guard surfaces as empty-string `latest_snapshot` and `days_stale`. Final sort by `int(days_stale)` DESC matches the SQL's `ORDER BY days_stale DESC`.

**`query_top_full_length_videos()`** implements the `(video_id, snapshot_date)` join from `BUSINESS_RULES.md`, section "Table grain and join keys (data contract)", via a filter-then-join pattern:

1. Compute `latest_common = min(MAX(video_metadata.snapshot_date), MAX(daily_video_stats.snapshot_date))`, the SQL's `LEAST(MAX, MAX)`.
2. Filter `video_metadata` rows to `snapshot_date == latest_common AND video_type == 'full_length'`.
3. Build a `{video_id: stats_row}` dict from `daily_video_stats` rows at `latest_common`.
4. Inner-join by dict lookup. The snapshot_date equality is already pinned, so the join key is effectively `(video_id, snapshot_date)`.
5. Sort by `int(view_count)` DESC.

Empty-source short-circuit returns `[]` (mirrors the SQL `IS NOT NULL` guard, sql/02 NULL-guard note).

**`query_eligible_video_count()`** reuses the same `latest_common` pattern, then within full-length rows at that snapshot counts the ones with `(today_phoenix - parse_published_at(published_at)).days >= 14`. The Phoenix-tz match here is the load-bearing detail: `published_at` is parsed via `datetime.fromisoformat(...)` against the loader's `-07:00`-offset ISO strings, `.date()` yields the Phoenix-local date, and the 14-day comparison runs against Phoenix-local today. This matches `DATE_DIFF(CURRENT_DATE("America/Phoenix"), DATE(m.published_at, "America/Phoenix"), DAY) >= 14` from the recipe's Step 5 SQL.

## JSON-shape parity (vs. 2026-05-25 live BigQuery JSON)

Compared against `runs/2026-05-25/queries/data_health.json` and `runs/2026-05-25/queries/top_full_length_videos.json`:

- `data_health`: keys match exactly (`days_stale`, `latest_snapshot`, `table_name`); all values are JSON strings; 4 rows, one per analytics table.
- `top_full_length_videos`: keys match exactly (`comment_count`, `days_since_published`, `duration_formatted`, `like_count`, `published_at`, `title`, `video_type`, `view_count`); all values are JSON strings; sort order is `view_count` DESC.
- `eligible_video_count`: one-row array with keys `eligible_count`, `total_full_length`, `latest_common_snapshot`; all-string values. Against the 2026-05-25 sample fixture (16 videos: 13 full-length, 3 shorts), produces `{"eligible_count": "11", "total_full_length": "13", "latest_common_snapshot": "2026-05-25"}`. Eligibility excludes VID012 (6 days) and VID013 (3 days), both under the 14-day boundary; consistent with the loader's `SAMPLE_VIDEOS` list.

The `published_at` string literal differs between live BQ (space-separated `"2025-11-07 13:01:07"`) and the CSV helper (full ISO with offset, e.g. `"2026-04-27T00:00:00-07:00"`). The shape contract (top-level array, key set, string-typed values) is preserved; the recipe consumes the JSON via `json.load`, never as a literal-format-sensitive string, so this difference does not affect downstream behavior.

## Acceptance verification (all PASS)

- `python3 -c "import ast; ast.parse(...)"` exits 0.
- `wc -l scripts/csv_query.py` = 210, within the 120-220 bound.
- `grep -cE '^def query_(...)' scripts/csv_query.py` = 3.
- `grep -cE 'from zoneinfo import ZoneInfo' scripts/csv_query.py` = 1.
- `grep -nE '^import (pandas|duckdb|numpy|requests)' scripts/csv_query.py` = 0 matches (stdlib-only confirmed).
- `grep -cE 'ZoneInfo\("America/Phoenix"\)' scripts/csv_query.py` = 2 occurrences (module constant `PHOENIX` and the inline `_today_phoenix` body uses the constant; the module constant counts as one literal usage; one literal usage is the acceptance floor).
- All three queries emit JSON arrays with the contracted shape; `unknown_query` rejected by argparse with exit code 2.
- Missing-CSV path raises `FileNotFoundError` mentioning `scripts/csv_fallback_loader.py` (verified against `--sample-dir /tmp/empty_sample_dir`).
- No em/en dashes; no banned vocabulary in either `scripts/csv_query.py` or the new CHANGELOG bullet.

## Commits

| Task | Hash | Message |
|---|---|---|
| 1 | `e846aa1` | feat(03-02): add CSV-mode query helper mirroring three live SQL queries |
| 2 | `64e7ed0` | docs(03-02): log CSV-mode query helper in CHANGELOG |

## Deviations from Plan

None. Plan executed exactly as written.

One minor judgment call worth noting: the plan said "if Plan 03-01's CHANGELOG entry under today's date already exists, ADD a new bullet under that same H2 section" while the repo's existing CHANGELOG pattern uses one H2 per topic/plan dated the same day (`## 2026-05-25, Phase 1 first end-to-end run`, `## 2026-05-25, Phase 1 scaffold fixups`, etc.). Followed the plan's explicit acceptance-criterion #6 ("no duplicate H2 for the same date") and appended the bullet to the existing `## 2026-05-25, Phase 3 Plan 03-01` H2, rewording the H2's lead paragraph to introduce both plans. This kept the date heading singular for the Phase 3 entries that landed today and matches the strict reading of the acceptance criterion.

## Threat-Model Coverage

All STRIDE entries in the plan's threat register received mitigation in the implementation:

- **T-03-02-01 (Tampering, query_name arg):** argparse `choices=sorted(QUERY_DISPATCH.keys())` enforces the allowed set; unknown values rejected with exit code 2 before any dispatch.
- **T-03-02-02 (Information disclosure, JSON injection):** all CSV values pass through `json.dump`, which escapes per JSON spec.
- **T-03-02-03 (Tampering, path traversal via --sample-dir):** developer escape hatch with no external trust boundary (CLI tool invoked locally by the operator's own recipe); disposition documented in plan.
- **T-03-02-04 (DoS, large CSVs):** accepted at fixture scale; `list(reader)` is reasonable for the 16-row `SAMPLE_VIDEOS` fixture.
- **T-03-02-SC (Supply-chain, new packages):** N/A confirmed; no third-party imports.

## Known Stubs

None. The helper is functionally complete and unit-callable. CSV-mode end-to-end behavior depends on Plan 03-03 wiring this helper into the `/run-analyzer` recipe; that is the next plan's scope, not a stub in this one.

## Threat Flags

None. No new network endpoints, auth paths, or trust-boundary surface introduced.

## Self-Check: PASSED

- `scripts/csv_query.py` exists: FOUND.
- `CHANGELOG.md` Plan 03-02 bullet present: FOUND (`head -40 CHANGELOG.md | grep -c "scripts/csv_query.py"` = 1).
- Commit `e846aa1` (feat task 1): FOUND in `git log`.
- Commit `64e7ed0` (docs task 2): FOUND in `git log`.
- End-to-end verification chain (AST + loader + all three queries + unknown-query rejection): all PASS.
- JSON-shape parity vs. live 2026-05-25 BigQuery JSON: keys match for both `data_health` and `top_full_length_videos`.
