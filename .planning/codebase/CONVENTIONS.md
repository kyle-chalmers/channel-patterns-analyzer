# Coding Conventions

**Analysis Date:** 2026-05-25

## Repo Character

This repo is not a traditional application codebase. It is a Claude-Code-driven analyzer where most of the "logic" lives in three places:

- **Prompt-as-code:** `CLAUDE.md` and `BUSINESS_RULES.md` (loaded as instructions on every analyzer session)
- **SQL queries:** `sql/01_*.sql` through `sql/04_*.sql` (data contracts and analysis)
- **Persistent artifacts:** `reports/{YYYY-MM-DD}.md`, `runs/{YYYY-MM-DD}/summary.json`

A single Python helper script lives at `scripts/csv_fallback_loader.py` for CSV-mode fallback. There is no application framework, no test suite, and no linter configuration committed.

Conventions below cover all four surfaces (Markdown prose, SQL, Python helper, persisted JSON).

## Naming Patterns

**Files:**
- Numeric-prefixed SQL: `sql/01_latest_snapshot_overview.sql`, `sql/02_top_full_length_videos.sql`. The two-digit prefix encodes run order and is required when adding new queries (see `docs/maintenance.md`).
- Snake_case Python module names: `scripts/csv_fallback_loader.py`.
- UPPERCASE root Markdown for policy/contract docs: `CLAUDE.md`, `BUSINESS_RULES.md`, `CHANGELOG.md`, `README.md`, `PROMPTS.md`, `LICENSE`.
- Lowercase Markdown for supporting docs: `docs/runbook.md`, `docs/schedule.md`, `docs/maintenance.md`, `docs/README.md`.
- Date-stamped artifacts use `YYYY-MM-DD` as the folder/file name: `reports/2026-05-24.md`, `runs/2026-05-24/`. Same-day re-runs append `-2`, `-3` (e.g., `reports/2026-05-24-2.md`).

**Directories:**
- Single-purpose, lowercase, plural where it holds many items: `sql/`, `scripts/`, `sample_data/`, `reports/`, `runs/`, `docs/`, `images/`.
- `.planning/` and `.internal/` are git-aware exclusions (`.internal/` is fully ignored; `.planning/` holds working artifacts).

**SQL identifiers:**
- snake_case columns: `video_id`, `snapshot_date`, `view_count`, `days_since_published`.
- snake_case derived columns with intent-revealing names: `views_per_day_since_publish_proxy`, `like_rate_pct`, `comment_rate_pct`. The `_proxy` suffix is meaningful — it flags non-strict metrics that need a label in the report (see `sql/03_age_controlled_performance.sql:42`).
- Lowercase table refs backticked: `` `youtube_analytics.video_metadata` ``.
- CTE names short and lowercase: `WITH latest_common AS (...)`, `WITH base AS (...)`.

**Python:**
- snake_case functions: `generate_video_metadata`, `generate_daily_video_stats`, `_format_duration`, `_write`.
- Leading underscore for module-private helpers: `_format_duration`, `_write` (`scripts/csv_fallback_loader.py:44,132`).
- UPPER_SNAKE for module constants: `REPO_ROOT`, `SAMPLE_DIR`, `SAMPLE_VIDEOS` (`scripts/csv_fallback_loader.py:18-41`).

**JSON fields:**
- snake_case keys throughout (`runs/README.md:32` schema): `run_date`, `run_started_at`, `bq_project`, `snapshot_dates`, `notion_write_ok`.

## Code Style

**Formatting (Python):**
- No `pyproject.toml`, no `setup.cfg`, no `.editorconfig`, no Black/Ruff/Prettier config committed.
- Observed Python style in `scripts/csv_fallback_loader.py`:
  - 4-space indentation.
  - Double-quoted strings.
  - Type hints on public function signatures: `def generate_video_metadata(snapshot: date) -> list[dict]:`.
  - `from __future__` imports not used; relies on Python 3.9+ for `list[dict]` builtin generics.
  - Module-level docstring at top, no per-function docstrings except where intent is non-obvious (`generate_daily_video_analytics` has a one-line note about pipeline staleness).
  - f-strings for interpolation (`scripts/csv_fallback_loader.py:46,61,141`).
  - `pathlib.Path` over `os.path`.

**Formatting (SQL):**
- Uppercase keywords: `SELECT`, `FROM`, `JOIN`, `WHERE`, `WITH`, `AS`, `USING`, `COUNT`, `GROUP BY`, `ORDER BY`, `LIMIT`.
- 4-space indentation for clauses inside `SELECT` and `WHERE`.
- Two-letter table aliases: `m` for `video_metadata`, `s` for `daily_video_stats` (see `sql/01_latest_snapshot_overview.sql:29-31`).
- `JOIN ... USING (video_id, snapshot_date)` — always join on the composite key, never on `video_id` alone (enforced by `BUSINESS_RULES.md` §4).
- `SAFE_DIVIDE` over `/` for any ratio that could divide by zero (`sql/03_age_controlled_performance.sql:42-44`).

**Linting:**
- No linter configured. Code style follows the conventions visible in existing files.

## Import Organization

**Python (`scripts/csv_fallback_loader.py:12-16`):**
1. Standard library only, alphabetical:
   ```python
   import csv
   import os
   import random
   from datetime import date, datetime, timedelta
   from pathlib import Path
   ```
2. No third-party imports anywhere in the repo by design (`requirements.txt` documents the BigQuery deps as optional/commented).
3. No relative imports — the repo has no package structure.

**Path Aliases:** Not applicable.

## Error Handling

**Python:** The helper script has no explicit error handling. It is a one-shot data generator; failure modes (missing directory) are handled implicitly (`SAMPLE_DIR.mkdir(parents=True, exist_ok=True)` at `scripts/csv_fallback_loader.py:135`).

**SQL:** Defensive patterns are encoded directly in the queries:
- `LEAST(MAX(...), MAX(...))` for cross-table latest-common-snapshot (`sql/01_latest_snapshot_overview.sql:15-20`).
- `SAFE_DIVIDE` for any ratio (`sql/03_age_controlled_performance.sql:42`).
- Explicit `WHERE` filters for age control (`days_since_published >= 14`) at `sql/03_age_controlled_performance.sql:35`.

**Analyzer (Claude session) error handling:** Governed by `CLAUDE.md` "When something blocks the run" and `docs/runbook.md`. The contract is: stop and surface the failure, write `runs/{run_date}/summary.json` with `errors: [...]` even on failure, never invent a report from partial data.

## Logging

**Framework:** `print()` in the Python helper (`scripts/csv_fallback_loader.py:141,146,151-156`). No logging library.

**Patterns:**
- The helper script prints progress per file written: `print(f"  wrote {len(rows)} rows -> {path.relative_to(REPO_ROOT)}")`.
- Bookend prints summarize what the script just did and what the user should do next.

**Analyzer logging:** Run metadata persists to `runs/{YYYY-MM-DD}/summary.json` and raw query results to `runs/{YYYY-MM-DD}/queries/*.json`. That folder is the audit log — see `runs/README.md` for the schema and `runs/README.md:32` for the canonical example.

## Comments

**When to Comment:**
- SQL files lead with a banner comment block explaining purpose, dataset assumptions, and any non-obvious logic. Example: `sql/03_age_controlled_performance.sql:1-16` documents why `views_per_day_since_publish_proxy` is labeled a proxy.
- Inline SQL comments call out invariants: timezone defaults, join-key requirements, references to `BUSINESS_RULES.md` sections.
- Python comments are sparse; the module docstring carries the explanation.

**SQL header pattern (use this when adding queries):**
```sql
-- ─── [Query name] ───────────────────────────────────────
-- [One-paragraph purpose and what the analyzer does with the output.]
--
-- Dataset name: [note about BQ_DATASET / project resolution]
--
-- [Any non-obvious caveats — proxy metrics, timezone assumptions, etc.]
```

**Docstrings (Python):** Module-level only, triple-quoted, with a `Usage:` block when invocation is non-trivial (`scripts/csv_fallback_loader.py:1-10`).

## Function Design

**Size:** Small. The largest function in `scripts/csv_fallback_loader.py` is `generate_daily_video_analytics` at ~25 lines.

**Parameters:** Type-hinted, positional. No keyword-only args.

**Return Values:** Explicit `list[dict]` returns from generators; `None` from writers and `main`.

**Determinism:** Stochastic helpers seed `random.Random(N)` with distinct seeds per table (`scripts/csv_fallback_loader.py:69,89,116`) so sample data is reproducible across runs. Follow this pattern for any future fixture generator.

## Module Design

**Exports:** No `__all__`. Top-level `main()` guarded by `if __name__ == "__main__":` (`scripts/csv_fallback_loader.py:159-160`).

**Barrel Files:** Not used. No package structure.

## Markdown / Prose Conventions

Carried from the user's global style rules and reinforced in `CLAUDE.md` § Voice:

- **No em dashes (—) or en dashes (–) as punctuation.** Use comma, period, parentheses, or a separate sentence.
- **No formulaic openers/closers** ("Great news!", "In conclusion,", "Overall,"). Start with the finding.
- **No reflexive jargon:** avoid "leverage", "robust", "seamless", "delve", "transformative", "elevated".
- **First-person plural** ("we tried", "what we are seeing") where it fits — analyzer and audience are figuring things out together.
- **Plain words, varied sentence length.** Short sentences land harder when the finding matters.
- **Tables and short bullets beat paragraphs** for scannable reports (`CLAUDE.md` § Report structure).
- **Observed vs. inferred vs. assumed** must be distinguished; never blur correlation into causation (`CLAUDE.md` § Never claim what the data does not support).

## Persistence / Artifact Conventions

- **Naming by run date, not snapshot date.** A run on 2026-05-24 pulling a 2026-05-22 snapshot writes `reports/2026-05-24.md`; the snapshot date goes into `summary.json`.
- **Always write `summary.json`, even on failure.** A failed run with `errors: [...]` is more useful than a missing folder (`runs/README.md:59`).
- **Same-day re-runs append `-2`, `-3`** to keep the original failure in the audit trail (`docs/maintenance.md:45`).
- **Commit raw query JSON** under `runs/{date}/queries/`. The dataset is small (~23 videos × 4 tables); committing the audit trail is intentional.

## Configuration Conventions

- **No hardcoded thresholds.** Anything quantitative (video age cutoff, sample-size confidence labels, fiscal year start) lives in `BUSINESS_RULES.md`. The analyzer reads them; queries reference them by section number in comments.
- **Environment via `.env`** (`.env.example` is the template). Required vars: `BQ_PROJECT`, `BQ_DATASET`, `NOTION_REPORT_PAGE_ID`, `DATA_SOURCE`, `SCHEDULE_TIMEZONE`.
- **Dataset name templated, not hardcoded.** SQL files use bare `youtube_analytics.<table>` and document that callers may template `${BQ_DATASET}` (`sql/01_latest_snapshot_overview.sql:6-9`).
- **`CHANGELOG.md` is required** for any change to `BUSINESS_RULES.md`, `sql/`, or analyzer behavior that would change a future report's numbers or framing.

---

*Convention analysis: 2026-05-25*
