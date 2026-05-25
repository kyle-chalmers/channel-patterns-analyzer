# External Integrations

**Analysis Date:** 2026-05-25

## APIs & External Services

**Data source:**
- Google BigQuery - Source of all analytics data. The analyzer queries the `youtube_analytics` dataset (four tables) via the `bq` CLI rather than a client library. See `sql/01_latest_snapshot_overview.sql` through `sql/04_data_health_check.sql` for the actual query patterns.
  - SDK/Client: `bq` CLI (Google Cloud SDK). Optional Python path: `google-cloud-bigquery>=3.20.0` (commented in `requirements.txt`).
  - Auth: `gcloud auth login` + `gcloud auth application-default login` for local; service-account key (env var) for the cloud routine.
  - Project: `BQ_PROJECT` env var; also resolved from active `gcloud` config.
  - Dataset: `BQ_DATASET` env var (default `youtube_analytics`).

**Output destination:**
- Notion - Write target for the weekly report. The analyzer does NOT call Notion directly; it hands a structured report to the `write-notion-report` Claude Code skill, which owns Notion block formatting and the API call.
  - SDK/Client: Notion MCP server locally, Notion web connector in the Anthropic cloud routine. See `docs/schedule.md` for why these are two different surfaces.
  - Auth: `NOTION_REPORT_PAGE_ID` env var; integration permissions managed in Notion.

**Upstream pipeline (out of repo):**
- `youtube-bigquery-pipeline` ([github.com/kyle-chalmers/youtube-bigquery-pipeline](https://github.com/kyle-chalmers/youtube-bigquery-pipeline)) - Loads the four `youtube_analytics.*` tables that this analyzer reads. When data is stale, the failure is almost always there, not in this repo. Documented as the first place to check in `docs/runbook.md` § "A required table is stale".

## Data Storage

**Databases:**
- BigQuery `youtube_analytics` dataset (four tables, joined on `(video_id, snapshot_date)`):
  - `video_metadata` - one row per `(video_id, snapshot_date)`
  - `daily_video_stats` - one row per `(video_id, snapshot_date)`
  - `daily_video_analytics` - one row per `(video_id, snapshot_date)`
  - `daily_traffic_sources` - one row per `(video_id, snapshot_date, traffic_source_type)`
  - Connection: `bq` CLI; project + dataset via env vars.
  - Client: `bq` CLI directly; no ORM.
  - Grain/join keys are codified in `BUSINESS_RULES.md` §4 and must be honored by every query.

**File Storage:**
- Local filesystem only. Persistent run artifacts live in the repo:
  - `reports/{YYYY-MM-DD}.md` - the published report, also committed
  - `runs/{YYYY-MM-DD}/summary.json` - run metadata
  - `runs/{YYYY-MM-DD}/queries/*.json` - raw SQL result dumps for the audit trail
  - `runs/{YYYY-MM-DD}/report.md` - mirror of the report for self-contained run folders
  - `sample_data/*.csv` - gitignored CSV fixtures from `scripts/csv_fallback_loader.py`

**Caching:**
- None. No Redis, Memcached, or in-process cache. Each weekly run is standalone (`CLAUDE.md` explicitly: "Treat every run as standalone").

## Authentication & Identity

**Auth Provider:**
- Google Cloud (for BigQuery)
  - Local: user OAuth via `gcloud auth login` + Application Default Credentials via `gcloud auth application-default login`.
  - Cloud routine: service account key passed as env var in the routine config. The cloud routine cannot see the operator's local `gcloud` login.
- Notion
  - Local: MCP server with workspace integration permissions on the target page.
  - Cloud routine: Notion connector authorized in the Anthropic account at claude.com.
- No application-level auth (no users, no sessions, no JWT, no OAuth flow in the repo). The analyzer is a single-tenant tool.

## Monitoring & Observability

**Error Tracking:**
- None as a service. Error capture is done by the analyzer itself, written to `runs/{YYYY-MM-DD}/summary.json` under the `errors: [...]` key (see `runs/README.md` for schema). `summary.json` is written even on failure.

**Logs:**
- The Claude Code session transcript is the run log. There is no structured logging framework.
- The `runs/` audit trail (per-run JSON + report mirror) functions as the historical log.

## CI/CD & Deployment

**Hosting:**
- Anthropic Claude Code Routines (cloud) - The scheduled weekly runs execute on Anthropic infrastructure. Configuration lives in the Anthropic UI (Routines → channel-patterns-analyzer), not the repo.
- Local Claude Code (operator's machine) - Ad-hoc and manual re-runs.

**CI Pipeline:**
- None. No `.github/workflows/`, no CI configuration in the repo.

## Environment Configuration

**Required env vars** (see `.env.example`):
- `DATA_SOURCE` - `bigquery` or `csv`
- `BQ_PROJECT` - GCP project ID
- `BQ_DATASET` - default `youtube_analytics`
- `YOUTUBE_CHANNEL_ID` - UC-prefixed channel ID
- `NOTION_REPORT_PAGE_ID` - Notion page UUID
- `ANALYSIS_LOOKBACK_DAYS` - default 90
- `MIN_VIDEO_AGE_DAYS` - default 14
- `SCHEDULE_TIMEZONE` - default `America/Phoenix`

**Secrets location:**
- Local: `.env` at repo root, gitignored.
- Cloud routine: per-routine environment configuration in the Anthropic UI.
- `.gitignore` also blocks `client_secret.json` and `*credentials*.json`. Service-account JSON keys, if used locally, must never be committed.
- The `.internal/` directory is gitignored and reserved for operator-only notes; do not place secrets there either.

## Webhooks & Callbacks

**Incoming:**
- None. The analyzer has no HTTP surface, no webhook endpoints, no API server.

**Outgoing:**
- BigQuery query calls via `bq` CLI (synchronous, request/response).
- Notion API calls indirectly through the `write-notion-report` skill (synchronous, request/response).
- No event-driven, webhook, or pub/sub integration.

## Scheduled / Triggered Execution

- Claude Code `/schedule` routine - Weekly trigger (Mondays at 9am `America/Phoenix` by default). The trigger is the routine's cron-equivalent, not a webhook. See `docs/schedule.md` for cadence and change instructions.

---

*Integration audit: 2026-05-25*
