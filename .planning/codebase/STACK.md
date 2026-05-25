# Technology Stack

**Analysis Date:** 2026-05-25

## Languages

**Primary:**
- Markdown - The bulk of the repo. `CLAUDE.md` and `BUSINESS_RULES.md` are the analyzer's executable instructions; `docs/*.md`, `reports/*.md`, and `runs/**/*.md` are operator and audit artifacts.
- SQL (BigQuery Standard SQL) - Analyzer queries in `sql/01_latest_snapshot_overview.sql`, `sql/02_top_full_length_videos.sql`, `sql/03_age_controlled_performance.sql`, `sql/04_data_health_check.sql`.

**Secondary:**
- Python 3 (stdlib only) - Single utility script `scripts/csv_fallback_loader.py` for generating fixture data. Uses `csv`, `os`, `random`, `datetime`, `pathlib`. No `__init__.py`, no package, no application code in Python.

## Runtime

**Environment:**
- Claude Code (Anthropic) - The analyzer itself is a Claude Code agent driven by `CLAUDE.md` + `@BUSINESS_RULES.md` import. There is no compiled or interpreted application process; the "runtime" is the LLM session loaded with project memory.
- `bq` CLI (Google Cloud SDK) - The data-access layer. `CLAUDE.md` instructs the agent to query via `bq query --use_legacy_sql=false`.
- `gcloud` CLI - Auth and project context for `bq`. `gcloud auth login` + `gcloud auth application-default login` + `gcloud config set project <id>`.
- Python 3 - Only required if the operator runs the CSV fallback script. Not required for the analyzer.

**Package Manager:**
- `pip` (for the optional Python deps in `requirements.txt`)
- Lockfile: Not present. `requirements.txt` is effectively empty (all real entries commented out).

## Frameworks

**Core:**
- Claude Code Skills - The `write-notion-report` skill is the handoff to Notion. It is gitignored (`.claude/skills/`) and lives at `.claude/skills/write-notion-report/SKILL.md` when installed locally. `CLAUDE.md` hands the report to this skill rather than calling Notion directly.
- Claude Code Routines (`/schedule`) - Weekly scheduled execution (Mondays 9am Phoenix). Routine config lives in the Anthropic UI, not in the repo. Local `routine_config.json` is gitignored.
- GSD framework - Optional planning/execution workflow scaffolding referenced in `README.md` and used to drive the build. Not a runtime dependency.

**Testing:**
- Not detected. No test framework, no `tests/` directory, no `pytest`/`unittest` files.

**Build/Dev:**
- No build step. The repo is configuration + prompts + SQL + docs. Nothing compiles or bundles.

## Key Dependencies

**Critical:**
- Google Cloud SDK (`gcloud` + `bq`) - The only hard external CLI dependency. Installed on macOS via `brew install --cask google-cloud-sdk`. Verified with `gcloud --version` and `bq version`.
- Claude Code CLI - Required to run the analyzer at all. Installed separately by the operator.

**Python (all optional, commented in `requirements.txt`):**
- `google-cloud-bigquery>=3.20.0` - Commented out. Only needed if the operator wants to call BigQuery from Python rather than through the `bq` CLI.
- `google-auth>=2.30.0` - Commented out. Pairs with the above.

The CSV fallback path (`scripts/csv_fallback_loader.py`) uses only Python stdlib — no third-party installs needed.

**Infrastructure:**
- BigQuery dataset `youtube_analytics` (configurable via `BQ_DATASET`) - Source of truth for all four analytics tables. Loaded upstream by [youtube-bigquery-pipeline](https://github.com/kyle-chalmers/youtube-bigquery-pipeline), which is out of repo.
- Notion workspace with a target page - Write target for the weekly report. Page ID held in `NOTION_REPORT_PAGE_ID` env var.

## Configuration

**Environment:**
- Single `.env` file at repo root, copied from `.env.example`. Gitignored.
- Loaded by the operator's shell and the Claude Code session; no `python-dotenv` or framework loader in the repo.

**Key configs required:**
- `DATA_SOURCE` - `bigquery` (default) or `csv`. Switches between live BigQuery and `./sample_data/*.csv`.
- `BQ_PROJECT` - GCP project ID holding the dataset. The `bq` CLI also reads this from active `gcloud` config.
- `BQ_DATASET` - Defaults to `youtube_analytics`. The bare dataset name is hardcoded in `sql/*.sql` files; operators are instructed to find-and-replace or template at query time.
- `YOUTUBE_CHANNEL_ID` - UC-prefixed channel ID for any channel-scoped filtering.
- `NOTION_REPORT_PAGE_ID` - Target Notion page UUID.
- `ANALYSIS_LOOKBACK_DAYS` - Default 90. Look-back window for weekly analysis.
- `MIN_VIDEO_AGE_DAYS` - Default 14. Threshold for inclusion in pattern claims (per `BUSINESS_RULES.md`).
- `SCHEDULE_TIMEZONE` - Default `America/Phoenix`. Anchors `CURRENT_DATE()` comparisons.

**Build:**
- No build config files. No `tsconfig.json`, `pyproject.toml`, `setup.py`, `Makefile`, or CI workflows in the repo.

## Platform Requirements

**Development:**
- macOS or Linux shell with `bash`/`zsh`.
- Google Cloud SDK installed and authenticated.
- Claude Code CLI installed and signed in.
- For the CSV fallback path only: Python 3 (any modern version with f-string + `pathlib`).

**Production:**
- "Production" is the Anthropic-hosted cloud routine, configured per-routine in the Anthropic UI (Routines → channel-patterns-analyzer). The routine needs:
  - Repo selected
  - Per-routine env vars (mirroring `.env`)
  - BigQuery service-account credentials (the cloud routine cannot use the operator's local `gcloud` login)
  - Notion web connector authorized in the Anthropic account (the cloud routine cannot see local MCP servers)
- See `docs/schedule.md` for the local-vs-cloud distinction; this is the project's most common operational failure surface.

---

*Stack analysis: 2026-05-25*
