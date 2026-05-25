# Channel Patterns Analyzer

## What This Is

A weekly automated analyst for the KC Labs AI YouTube channel. Each run, a Claude Code session queries the `youtube_analytics` BigQuery dataset, applies the analyzer rules in `CLAUDE.md` + `BUSINESS_RULES.md` (age control, small-sample hedging, brutal honesty about underperformance), and publishes a structured report to a Notion page via a project-local `write-notion-report` skill. The audience is one person — Kyle — and the goal is an honest second pair of eyes on the channel's data, not a marketing dashboard.

## Core Value

Every run produces a report that distinguishes observed, inferred, and assumed claims, hedges small samples, and applies fair age-normalized comparisons. If the report drifts into hype, false confidence, or stale-data blindness, the analyzer has failed regardless of how polished the output looks.

## Requirements

### Validated

<!-- Inferred from existing scaffold + commits. The "executable instructions" layer (CLAUDE.md, BUSINESS_RULES.md, SQL patterns, persistent folders) is shipped and works against live BigQuery. -->

- ✓ **Analyzer voice + reasoning contract** lives in `CLAUDE.md` with `@BUSINESS_RULES.md` import — existing (commits `7e09b0f`, `f53f330`)
- ✓ **Domain data contract** (fiscal year, table grain, join keys, refresh expectations) lives in `BUSINESS_RULES.md` — existing
- ✓ **Read-only SQL pattern library** at `sql/01_latest_snapshot_overview.sql`, `sql/02_top_full_length_videos.sql`, `sql/03_age_controlled_performance.sql`, `sql/04_data_health_check.sql` — existing
- ✓ **CSV fallback loader** at `scripts/csv_fallback_loader.py` generates fixture data mirroring BigQuery schemas — existing
- ✓ **Persistent run structure** (`reports/{date}.md`, `runs/{date}/summary.json`, `runs/{date}/queries/*.json`) — existing (commit `7e09b0f`)
- ✓ **Operator docs** (`docs/runbook.md`, `docs/maintenance.md`, `docs/schedule.md`) — existing
- ✓ **BigQuery connectivity verified** — `bq` CLI authenticated, smoke query against `youtube_analytics.video_metadata` succeeded (129 videos, snapshot 2026-05-24)
- ✓ **README setup walkthrough** for gcloud/bq install + two-step auth + dataset configuration — existing (README §3.1–3.6)

### Active

<!-- The remaining build to reach a working end-to-end weekly run. -->

- [ ] **DATA-HEALTH-01** — Analyzer run begins with a data-health check that emits the latest `snapshot_date` per analytics table and flags any table older than `CURRENT_DATE() - 3` in America/Phoenix, surfaced in the report's "Data Health" section before any analysis
- [ ] **BQ-01** — `bq` CLI wrapper pattern that respects `$BQ_PROJECT` and `$BQ_DATASET` env vars (substituting `$BQ_DATASET` into SQL files before execution) and returns parsed JSON results for downstream analysis
- [ ] **BQ-02** — Query results from each canonical SQL file get dumped to `runs/{date}/queries/*.json` for the audit trail
- [ ] **ANALYSIS-01** — Age-control logic enforced: videos with `days_since_published < 14` excluded from "top performers" / pattern claims; cross-age comparisons use first-30-day windows or labeled views-per-day proxy
- [ ] **ANALYSIS-02** — Small-sample hedging applied: live video count queried each run from `video_metadata`; confidence labels (low / moderate / standard) appended next to claims based on the thresholds in `CLAUDE.md`
- [ ] **ANALYSIS-03** — Six-section report structure (Data Health → Headline → What's working → What's not working → Patterns worth watching → Open questions) consistently produced and reviewed against the most recent 3–4 prior reports before drafting
- [ ] **NOTION-01** — `write-notion-report` Skill at `.claude/skills/write-notion-report/SKILL.md` accepts the structured report from the analyzer and writes it to the channel-patterns Notion page, returning a permalink or page ID; works against both the local Notion MCP server and the cloud Notion connector (claude.ai routine context)
- [ ] **NOTION-02** — Notion target page resolved via `NOTION_PAGE_ID` env var (in `.env`, gitignored); each run appends a new child page named with the run date
- [ ] **NOTION-03** — Skill writes Notion blocks (headings, tables, callouts for data-health flags) that mirror the markdown report structure — analyzer does not format Notion blocks itself
- [ ] **PERSIST-01** — Same report saved to `reports/{run_date}.md` (run date, not snapshot date) and `runs/{run_date}/summary.json` written with snapshot dates per table, video count, query row counts, errors, durations
- [ ] **PERSIST-02** — Local artifacts always written even if Notion write fails; failure surfaced in `summary.json` and to the operator
- [ ] **CSV-01** — `DATA_SOURCE=csv` path: every BigQuery query has a CSV-backed equivalent reading from `sample_data/*.csv`; analyzer behavior is identical except for data-health timestamps
- [ ] **SCHEDULE-01** — `/schedule` routine documented in `docs/schedule.md` for weekly Monday 9am Phoenix runs, with both local and cloud variants
- [ ] **ERROR-01** — Failure modes (bq auth fail, missing table, empty table, Notion write fail) each map to the relevant `docs/runbook.md` section and produce a `summary.json` with the error so the run never silently degrades

### Out of Scope

- **A web UI / dashboard** — the consumer is Kyle reading Notion; building a frontend defeats the "honest analyst" framing
- **Causal inference / experiment design** — analyzer reports correlation and flags hypotheses; it does not claim to prove cause
- **Cross-channel benchmarking** — single channel only; competitor data is not part of the dataset contract
- **Real-time / sub-daily refresh** — weekly cadence is the explicit design point; sub-daily refresh would change the role from analyst to alerting
- **BigQuery ingest / ETL** — upstream ingest pipeline is owned elsewhere; analyzer only reads
- **A Python application orchestrator** — the analyzer is a Claude Code session driven by `CLAUDE.md`, not a Python program; rejected in questioning to keep the "AI analyst" feel
- **Cost preview / dry-run guards on every query** — dataset is small (~24 videos, ~10k rows); SQL discipline + scope notes in `CLAUDE.md` are sufficient
- **Cadence detection beyond weekly** — `RUN_WINDOW` env vars and elapsed-day math add surface area for no clear benefit at this stage
- **Cloud-side scheduling owned by this repo** — the `/schedule` routine config lives in the Anthropic UI, not in the repo

## Context

- **Public-facing repo** companion to a YouTube video. Anything sensitive (page IDs, project IDs, recording notes) lives in `.internal/` or `.env`, both gitignored. The repo is meant to be forkable by viewers.
- **Brownfield state at planning time:** the runtime contract (`CLAUDE.md` + `BUSINESS_RULES.md`), SQL pattern library, persistent folder layout, and operator docs are already in place. BigQuery connectivity is verified end-to-end against the real `youtube_analytics` dataset. Notion connectivity is configured locally (MCP) and in the cloud (claude.ai connector) but no `write-notion-report` Skill exists yet.
- **YouTube channel:** https://www.youtube.com/@kylechalmersdataai. ~24 full-length videos at planning time (live-queried each run; never hardcoded). Small sample is a real constraint on every pattern claim the analyzer makes.
- **Data freshness reality:** as of 2026-05-24, `video_metadata` is fresh (today's snapshot) but `daily_video_analytics` and `daily_traffic_sources` are 89 days stale — the data-health check is the most important section of the first report.
- **Voice:** KC Labs — humble, evidence-based, learning together with the audience. No em dashes, no AI-voice vocabulary ("leverage", "robust", "delve"), no formulaic openers. The analyzer's prose is held to the same bar as the channel's video scripts.

## Constraints

- **Tech stack — bq CLI, not Python BigQuery client.** SQL files + `bq query --use_legacy_sql=false` is the canonical query path. Python BigQuery is explicitly avoided so the analyzer reads as a "shell + SQL + Claude" stack viewers can replicate without learning a Python SDK.
- **Tech stack — no application framework.** No FastAPI, no Click CLI, no orchestration framework. The analyzer is a Claude Code session reading `CLAUDE.md`. New code is only added when a markdown rule can't express the behavior.
- **Tech stack — Skills, not direct MCP calls in CLAUDE.md.** The `write-notion-report` Skill is the only place that touches Notion. The analyzer hands the Skill a structured report; the Skill owns Notion block formatting and transport (MCP locally, connector in cloud).
- **Public repo — no secrets, no PII.** Page IDs, project IDs, recording notes never get committed. `.internal/` and `.env` are gitignored. The `write-notion-report` Skill must read `NOTION_PAGE_ID` from env, not hardcode it.
- **Dependencies — minimum viable.** `gcloud` + `bq` are hard. Python is only needed for the CSV fallback loader and uses stdlib only. No new Python packages added without explicit justification.
- **Idempotency — runs are deterministic given inputs.** Same snapshot date + same SQL files = same report. Side effects (Notion write, file writes) tolerate retry; failed Notion writes do not lose the local report.
- **Cost — small dataset, SQL discipline.** No automated query cost guards. Scoped queries with filters/LIMIT are a documented rule in `CLAUDE.md`.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Analyzer runs as a Claude Code session (SQL + bq CLI), not a Python orchestrator | Matches the "AI analyst" role in CLAUDE.md; viewers see prompt engineering as the product, not Python plumbing | — Pending |
| `write-notion-report` Skill is project-local (`.claude/skills/write-notion-report/`) and committed to the repo | Ships with the analyzer; viewers can fork and use as-is. Requires un-gitignoring `.claude/skills/write-notion-report/` specifically (other skills can stay local-only) | — Pending |
| Notion writer supports both local MCP and cloud connector | Same Skill works for terminal-driven runs and `/schedule` cloud routines without duplicating logic | — Pending |
| Notion target via `NOTION_PAGE_ID` in `.env`, new child page per run | Deterministic, no search calls, no schema setup. Keeps secrets out of the repo. | — Pending |
| CSV fallback (`DATA_SOURCE=csv`) is first-class — every query path supports both | Lets contributors / viewers without BigQuery access run the analyzer end-to-end | — Pending |
| Weekly cadence only — no `RUN_WINDOW` env var, no cadence detection | YAGNI; current design is weekly via `/schedule`; revisit only if cadence actually changes | — Pending |
| BigQuery cost guards: documentation only, no automated wrapper | ~24 videos, ~10k rows; soft cap adds noise. Revisit if the dataset grows 10×+. | — Pending |
| Phase mode: Vertical MVP (each phase delivers an end-to-end usable analyzer slice) | Live-build context — every phase should produce something that runs against real BigQuery and writes a real Notion page. | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-24 after initialization*
