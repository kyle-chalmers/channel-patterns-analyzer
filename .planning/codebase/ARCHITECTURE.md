<!-- refreshed: 2026-05-25 -->
# Architecture

**Analysis Date:** 2026-05-25

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                Trigger Layer (Layer 4: Workflows)            │
│   Claude Code /schedule routine (Mon 9am America/Phoenix)    │
│   Configured in Anthropic web UI, not in the repo            │
└────────────────────────────┬─────────────────────────────────┘
                             │ spawns fresh Claude Code session
                             ▼
┌─────────────────────────────────────────────────────────────┐
│             Instructions Layer (Layer 1)                     │
│   `CLAUDE.md`  →  voice + reasoning + run protocol           │
│       @-imports `BUSINESS_RULES.md`  (Layer 2: Structure)    │
│   The "code" of this repo is prose. Claude is the runtime.   │
└────────────────────────────┬─────────────────────────────────┘
                             │ executes analyzer protocol
         ┌───────────────────┼───────────────────────┐
         ▼                   ▼                       ▼
┌──────────────────┐ ┌──────────────────┐ ┌────────────────────┐
│  SQL Templates   │ │  Memory / Prior  │ │  CSV Fallback Gen  │
│  (Tools, L3)     │ │     Reports      │ │  (dev-only path)   │
│  `sql/*.sql`     │ │  `reports/*.md`  │ │ `scripts/csv_      │
│  Numeric prefix  │ │  last 3-4 read   │ │  fallback_loader.  │
│  = run order     │ │  to calibrate    │ │  py`               │
└────────┬─────────┘ └──────────────────┘ └─────────┬──────────┘
         │                                          │
         ▼                                          ▼
┌──────────────────────────┐              ┌──────────────────────┐
│  BigQuery via `bq` CLI   │  (primary)   │  Local CSVs          │
│  Dataset: $BQ_DATASET    │ ─── or ───   │  `sample_data/*.csv` │
│  4 tables, snapshot-     │              │  Same schema as BQ   │
│  partitioned             │              │  (DATA_SOURCE=csv)   │
└────────────┬─────────────┘              └──────────┬───────────┘
             │                                       │
             └───────────────────┬───────────────────┘
                                 ▼
                  ┌────────────────────────────────┐
                  │   Analyzer reasoning           │
                  │   (Claude, in-session)         │
                  │   Applies BUSINESS_RULES.md:   │
                  │   age control, sample-size     │
                  │   hedging, FY anchor, grain    │
                  └───────────────┬────────────────┘
                                  │ produces structured report
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
┌──────────────────────┐ ┌──────────────────┐ ┌────────────────────┐
│ write-notion-report  │ │ reports/         │ │ runs/{run_date}/   │
│ Skill (ungitted)     │ │ {run_date}.md    │ │ summary.json       │
│ `.claude/skills/`    │ │ (Notion mirror + │ │ queries/*.json     │
│ Local MCP (terminal) │ │  analyzer memory)│ │ report.md          │
│ Web connector (cloud)│ │                  │ │ (audit trail)      │
│   ↓                  │ │                  │ │                    │
│ Notion channel-      │ │                  │ │                    │
│ patterns page        │ │                  │ │                    │
└──────────────────────┘ └──────────────────┘ └────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Instructions (Layer 1) | Analyzer voice, reasoning rules, run protocol, report structure | `CLAUDE.md` |
| Business Rules (Layer 2) | Stable domain facts: fiscal calendar, exclusions, data-refresh contract, per-table grain and join keys | `BUSINESS_RULES.md` |
| SQL Templates (Layer 3) | Read-only query patterns the analyzer runs against BigQuery | `sql/01_*.sql` ... `sql/04_*.sql` |
| CSV Fallback (dev tool) | Generates sample data matching the BQ schema for the no-BigQuery path | `scripts/csv_fallback_loader.py` |
| Reports Archive (Layer 4) | Human-readable weekly outputs; also the analyzer's calibration memory | `reports/{YYYY-MM-DD}.md` |
| Run Audit Trail (Layer 4) | Per-run metadata, raw query JSON, report mirror | `runs/{YYYY-MM-DD}/` |
| Operator Manual | Runbook, maintenance guide, schedule notes | `docs/runbook.md`, `docs/maintenance.md`, `docs/schedule.md` |
| Change Log | One-line audit of behavior-changing edits | `CHANGELOG.md` |
| Notion Write Skill | Encapsulates Notion publishing; ungitted, generated per environment | `.claude/skills/write-notion-report/SKILL.md` (gitignored) |
| Routine Config | Cloud `/schedule` definition (cadence, env vars, connectors); also ungitted | `routine_config.json` (gitignored) |
| Prompt Playbook | The 10 prompts that build the analyzer in the companion video | `PROMPTS.md` |

## Pattern Overview

**Overall:** Prompt-driven agent. Markdown files are the source code; the LLM is the runtime. SQL is templated; persistence is filesystem-based; outbound side effects (Notion writes) are delegated to a Claude Code Skill.

**Key Characteristics:**
- No service process, no application code. Claude Code executes `CLAUDE.md` as its operating manual on each scheduled fire.
- Strong separation between policy (`CLAUDE.md`, `BUSINESS_RULES.md`) and queries (`sql/`). Policy governs how to read query results, never the other way around.
- Persistence-as-memory: the analyzer reads `reports/` to calibrate confidence across weeks while keeping each report standalone in tone.
- Two execution surfaces (local terminal vs. cloud routine) deliberately separated; tools (bq auth, Notion access) are wired differently in each, documented in `docs/schedule.md`.
- Audit-trail-first: every run writes `runs/{run_date}/summary.json` and raw query dumps, even on failure.

## Layers

**Layer 1 — Instructions (`CLAUDE.md`):**
- Purpose: Defines voice, brutal-honesty norm, age-control mechanics, sample-size thresholds, report section order, and persistent-structure protocol.
- Location: `CLAUDE.md` (repo root, loaded automatically by Claude Code).
- Depends on: `BUSINESS_RULES.md` via `@BUSINESS_RULES.md` import.
- Used by: every Claude Code session in this repo, including the scheduled routine.

**Layer 2 — Structure (`BUSINESS_RULES.md`):**
- Purpose: Stable domain facts that outlive any one session: fiscal year (July anchor), data-health expectations, per-table grain, join-key contract.
- Location: `BUSINESS_RULES.md` (repo root).
- Depends on: nothing.
- Used by: `CLAUDE.md` and every SQL file's comment header.

**Layer 3 — Tools (SQL templates + bq CLI + Notion MCP/connector):**
- Purpose: External system access. `sql/` holds the query patterns; the `bq` CLI is the data path in; the `write-notion-report` Skill (plus MCP/connector) is the data path out.
- Location: `sql/*.sql`, plus the gitignored `.claude/skills/write-notion-report/`.
- Depends on: ambient `gcloud`/`bq` auth, env vars (`BQ_PROJECT`, `BQ_DATASET`, `NOTION_REPORT_PAGE_ID`).
- Used by: the analyzer at run time.

**Layer 4 — Workflows (`/schedule` + persistence):**
- Purpose: Make the analyzer recurring and durable. The routine fires it; `reports/`, `runs/`, `docs/`, and `CHANGELOG.md` give it memory and an audit trail.
- Location: `reports/`, `runs/`, `docs/`, `CHANGELOG.md`. Routine itself lives in the Anthropic UI, not the repo.
- Depends on: filesystem write access in the session, working Notion path.
- Used by: future runs (memory) and Kyle reviewing why a past report said what it said (audit).

## Data Flow

### Primary Request Path (scheduled weekly run)

1. `/schedule` routine fires Monday 9am America/Phoenix and spins up a fresh Claude Code session against this repo. (`docs/schedule.md`)
2. Claude Code auto-loads `CLAUDE.md`, which `@`-imports `BUSINESS_RULES.md` at the first content reference.
3. Analyzer runs Data Health first: executes `sql/04_data_health_check.sql` via `bq query --use_legacy_sql=false` and confirms each of the four `youtube_analytics` tables has a snapshot within the last 3 days per `BUSINESS_RULES.md` §3.
4. Analyzer runs the remaining numbered SQL in `sql/` (`01_latest_snapshot_overview.sql`, `02_top_full_length_videos.sql`, `03_age_controlled_performance.sql`), applying `WHERE m.snapshot_date = MAX(...)` and the `(video_id, snapshot_date)` join key from `BUSINESS_RULES.md` §4.
5. Analyzer reads the most recent 3–4 entries in `reports/` to calibrate confidence labels and avoid restating findings verbatim (`CLAUDE.md` § Persistent structure).
6. Analyzer drafts the report against the fixed section order in `CLAUDE.md` § Report structure: Data Health → Headline → What is working → What is not working → Patterns worth watching → Open questions.
7. Analyzer hands the structured report to the `write-notion-report` Skill at `.claude/skills/write-notion-report/SKILL.md` (gitignored), which publishes to the `NOTION_REPORT_PAGE_ID` page via Notion MCP (terminal) or the web connector (cloud routine).
8. Analyzer writes `reports/{run_date}.md`, `runs/{run_date}/summary.json`, `runs/{run_date}/queries/*.json`, and `runs/{run_date}/report.md` — even if the Notion write in step 7 failed.

### CSV Fallback Path (no BigQuery)

1. User runs `python scripts/csv_fallback_loader.py` once to produce `sample_data/*.csv` with the four BQ-equivalent schemas.
2. User sets `DATA_SOURCE=csv` in `.env`.
3. Analyzer reads from `./sample_data/*.csv` instead of issuing `bq query` calls; downstream reasoning is identical because schemas match.

### Failure Path

1. Any step that errors (bq auth, missing table, Notion write) is captured into `runs/{run_date}/summary.json.errors` and surfaced in the report's Data Health section.
2. Recovery routes through `docs/runbook.md`; new failure modes get added to the runbook as part of the fix (`docs/maintenance.md`).
3. Re-runs land at `reports/{run_date}-2.md` and `runs/{run_date}-2/` to preserve the original failure in the audit trail.

**State Management:**
- No in-memory state across runs. State is filesystem state: `reports/`, `runs/`, `CHANGELOG.md`.
- BigQuery is the system of record for inputs; `youtube-bigquery-pipeline` (separate repo) is upstream.
- Notion is a publish target, not a source of truth.

## Key Abstractions

**Run date vs. snapshot date:**
- Purpose: Separates when the analyzer fired from when the data was last refreshed upstream.
- Examples: `reports/2026-05-24.md` is the run date; the inner Data Health section records the snapshot date per table.
- Pattern: Filenames everywhere use **run date**. Snapshot dates appear inside `summary.json` under `snapshot_dates`.

**Latest common snapshot:**
- Purpose: Avoid silently dropping rows when one table has caught up but another hasn't.
- Examples: `sql/01_latest_snapshot_overview.sql` uses `LEAST(MAX(metadata), MAX(stats))`; `BUSINESS_RULES.md` §4 generalizes this as `MIN(MAX(snapshot_date))` across joined tables.
- Pattern: Always join on `(video_id, snapshot_date)`, never on `video_id` alone.

**Age control:**
- Purpose: Prevent direct comparisons between a 3-day-old video and a 1-year-old video.
- Examples: `sql/03_age_controlled_performance.sql` excludes `days_since_published < 14` and computes `views_per_day_since_publish_proxy`.
- Pattern: The SQL produces raw signal; the analyzer applies the policy from `CLAUDE.md` § Age control.

**Confidence label:**
- Purpose: Force every pattern claim to carry a sample-size disclosure.
- Examples: "low confidence (small sample)" for fewer than 5 videos, "moderate" for 5–10, no label at 10+.
- Pattern: Labels go inline with the claim in the report, not in a footnote.

## Entry Points

**Scheduled run (cloud):**
- Location: Anthropic UI → Routines → `channel-patterns-analyzer` (config is not in the repo).
- Triggers: cron-like cadence, default Monday 9am America/Phoenix.
- Responsibilities: Provision env vars, repo access, Notion web connector, BQ service-account credentials; then spawn a Claude session that loads `CLAUDE.md`.

**Manual run (local):**
- Location: `cd channel-patterns-analyzer && claude` then prompt "Run the analyzer."
- Triggers: operator command.
- Responsibilities: Same as scheduled path, but uses the operator's `gcloud` login and local Notion MCP instead of cloud credentials.

**CSV fallback generation:**
- Location: `scripts/csv_fallback_loader.py`.
- Triggers: `python scripts/csv_fallback_loader.py`.
- Responsibilities: Writes deterministic-ish sample data (seeded RNG) to `sample_data/` so the analyzer path works without BigQuery.

## Architectural Constraints

- **No application runtime:** There is no Python service, no daemon. The repo is prose + SQL + sample-data generator. Claude Code is the only execution engine. Adding a long-running service would break the model.
- **Bare-dataset SQL convention:** SQL files reference `` `youtube_analytics.<table>` `` without a project prefix; the `bq` CLI resolves the project from active `gcloud` config (`sql/01_latest_snapshot_overview.sql` header). Forks with a different dataset name must template `$BQ_DATASET` at run time per `docs/maintenance.md`.
- **Numeric SQL prefixes are run order:** `sql/01_*.sql` runs before `sql/02_*.sql`. New queries must take the next prefix.
- **Timezone discipline:** `BUSINESS_RULES.md` §3 anchors staleness in America/Phoenix; `sql/04_data_health_check.sql`'s `CURRENT_DATE()` should be wrapped as `CURRENT_DATE("America/Phoenix")` when run against a UTC-default BigQuery.
- **Skill + routine are gitignored:** `.claude/skills/` and `routine_config.json` are listed in `.gitignore`. They get regenerated per environment. Treat their absence as expected, not as missing files.
- **Internal vs. public split:** `.internal/` is gitignored for personal notes and recording materials; everything else is public-facing per the public-repo policy.
- **No silent retcons:** Reports never get backfilled or edited after publish (`docs/maintenance.md`); a fresh run on the same day uses suffix `-2`, `-3`.

## Anti-Patterns

### Joining tables on `video_id` alone

**What happens:** `JOIN youtube_analytics.daily_video_stats USING (video_id)` instead of `USING (video_id, snapshot_date)`.
**Why it's wrong:** Each table is snapshot-partitioned with one row per `(video_id, snapshot_date)` per `BUSINESS_RULES.md` §4. Joining on `video_id` alone Cartesian-explodes across every historical snapshot pair.
**Do this instead:** Always `USING (video_id, snapshot_date)` as shown in `sql/01_latest_snapshot_overview.sql:30-31` and `sql/02_top_full_length_videos.sql:25-26`.

### Joining `daily_traffic_sources` before aggregating

**What happens:** Joining `daily_traffic_sources` directly to the other three tables.
**Why it's wrong:** Its grain is `(video_id, snapshot_date, traffic_source_type)` (`BUSINESS_RULES.md` §4) — multiple rows per `(video_id, snapshot_date)`. A naive join multiplies stats rows by source-type count.
**Do this instead:** `SUM(views) GROUP BY video_id, snapshot_date` first, then join, as the §4 contract spells out.

### Reporting on videos under 14 days old

**What happens:** Pulling fresh uploads into "top performers" or pattern claims.
**Why it's wrong:** `CLAUDE.md` § Age control excludes them; the comparison is mathematically misleading and the audience can tell.
**Do this instead:** `sql/03_age_controlled_performance.sql:35` filters `days_since_published >= 14`. If a young video must be mentioned, label it low-confidence and show the age column next to the metric.

### Hardcoding sample sizes or thresholds

**What happens:** Writing "the channel has 24 videos" into analysis prose.
**Why it's wrong:** The video count changes weekly. `CLAUDE.md` § Small samples requires querying `video_metadata` at the start of every run and applying thresholds against the live number.
**Do this instead:** Query the count; thresholds (5, 10) live in `CLAUDE.md` and apply against the queried value.

### Calling Notion directly

**What happens:** The analyzer formats Notion blocks itself or calls the Notion API.
**Why it's wrong:** Per `CLAUDE.md` § Your role, the `write-notion-report` Skill owns the Notion write. Bypassing it splits responsibility and bypasses error handling.
**Do this instead:** Hand the finished structured report to the Skill; let it own block formatting and MCP/connector selection.

### Falling back to stale data without flagging

**What happens:** A BQ auth failure prompts the analyzer to read yesterday's `runs/.../queries/*.json` and produce a report.
**Why it's wrong:** `CLAUDE.md` § When something blocks the run forbids this. A silent stale-data report is worse than a clear failure.
**Do this instead:** Stop, surface the error, write `runs/{run_date}/summary.json` with the failure captured, leave Notion untouched.

### Causal language from correlation

**What happens:** "X in the title caused more views."
**Why it's wrong:** `CLAUDE.md` § Never claim what the data does not support draws a hard line. The dataset shows correlation; the analyzer cannot establish causation.
**Do this instead:** "Videos with X in the title got more views" — and label the sample size.

## Error Handling

**Strategy:** Fail loud, fail recorded, fail recoverable.

**Patterns:**
- Data Health is the first section of every report. Stale tables, missing tables, and empty queries surface there before any analysis.
- `runs/{run_date}/summary.json.errors` is the structured failure log. It gets written on every run, including partial or failed runs.
- Recovery paths are documented per failure mode in `docs/runbook.md`. New failure modes get added to the runbook as part of the fix.
- Notion write failures do not lose work: `reports/{run_date}.md` and `runs/{run_date}/` still get written locally so re-publishing is a separate manual step.

## Cross-Cutting Concerns

**Logging:** `runs/{run_date}/summary.json` is the structured log per run. Schema in `runs/README.md`.

**Validation:** Data-contract checks happen in two places — `sql/04_data_health_check.sql` for staleness, `CLAUDE.md` rules for grain/join/age/sample size at analysis time.

**Authentication:**
- BigQuery: `gcloud auth login` + `gcloud auth application-default login` locally; service-account key in routine env vars in the cloud (`docs/schedule.md`).
- Notion: local MCP server in terminal sessions, web connector in cloud routines.

**Configuration:** Env vars in `.env` (local) or routine env vars (cloud), templated from `.env.example`. `.env` is gitignored.

**Voice consistency:** `CLAUDE.md` § Voice and the global Prose & Anti-AI-Voice rules govern every report. No em dashes, no "leverage"/"seamless"/"robust", first person plural where it fits.

---

*Architecture analysis: 2026-05-25*
