# Requirements: Channel Patterns Analyzer

**Defined:** 2026-05-24
**Core Value:** Every weekly run produces a Notion report that distinguishes observed / inferred / assumed claims, hedges small samples, applies age-normalized comparisons, and is brutally honest about underperformance.

## v1 Requirements

Requirements for the first end-to-end weekly run. Each maps to a roadmap phase.

### Data Health

- [ ] **HEALTH-01**: Analyzer's first step queries each of the four `youtube_analytics` tables (`video_metadata`, `daily_video_stats`, `daily_video_analytics`, `daily_traffic_sources`) for `MAX(snapshot_date)` and writes the result to `runs/{run_date}/queries/data_health.json`
- [ ] **HEALTH-02**: Any table whose latest `snapshot_date` is older than `CURRENT_DATE('America/Phoenix') - 3` is flagged as stale, with the stale-by-N-days delta surfaced
- [ ] **HEALTH-03**: The report's Data Health section is rendered first, names every stale table explicitly, and downstream sections that depend on a stale table must say so in the report (no silent analysis over stale data)

### BigQuery Access

- [ ] **BQ-01**: SQL files in `sql/` execute via `bq query --use_legacy_sql=false --format=json`, substituting `$BQ_DATASET` (default `youtube_analytics`) into the SQL text before execution
- [ ] **BQ-02**: Each canonical query result is written to `runs/{run_date}/queries/{query_name}.json` for the audit trail
- [ ] **BQ-03**: BigQuery auth failures, missing-table errors, and empty-result errors each stop the run with a clear message mapped to `docs/runbook.md`; the analyzer never falls back to silently producing a report against missing data

### CSV Fallback

- [ ] **CSV-01**: When `DATA_SOURCE=csv`, the analyzer reads from `sample_data/*.csv` and produces a structurally identical report; only the data-health timestamps differ
- [ ] **CSV-02**: Every BigQuery query path has a CSV-backed equivalent — no analyzer behavior is BigQuery-only

### Analysis Rules

- [x] **ANALYSIS-01**: Videos with `days_since_published < 14` are excluded from "top performers" and pattern claims; flagged as low-confidence if mentioned at all
- [x] **ANALYSIS-02**: Cross-age comparisons normalize to a comparable window (first-30-day views when possible; views-per-day-since-publish as a labeled proxy otherwise)
- [x] **ANALYSIS-03**: Live video count queried each run from `video_metadata` (latest snapshot); confidence label (low / moderate / standard) appended next to every pattern claim per the thresholds in `CLAUDE.md`
- [x] **ANALYSIS-04**: Trending claims require at least 14 days of data per video in the comparison set
- [x] **ANALYSIS-05**: Before drafting, the analyzer reads the three most recent `reports/{date}.md` files to calibrate confidence (upgrade patterns with more data) and avoid restating findings verbatim

### Report Structure

- [x] **REPORT-01**: Each report has the six required sections in order: Data Health, Headline, What is working, What is not working, Patterns worth watching, Open questions
- [x] **REPORT-02**: Findings include numbers, age context, and confidence labels in plain sight (not footnotes)
- [x] **REPORT-03**: Voice rules enforced — no em dashes, no banned vocabulary list ("leverage", "robust", "delve", etc.), no formulaic openers/closers; written in first-person plural where it fits

### Notion Writer Skill

- [ ] **NOTION-01**: A Claude Code Skill called `write-notion-report` lives at `.claude/skills/write-notion-report/SKILL.md` (project-local, committed to the repo) with clear when-to-use instructions that trigger invocation whenever the analyzer hands off a completed report dictionary
- [ ] **NOTION-02**: The Skill accepts a **structured report dictionary** (keys: `run_date`, `data_health`, `headline`, `working`, `not_working`, `patterns`, `open_questions`, plus the markdown body) as its input contract; the analyzer's job ends when it produces this dictionary and invokes the Skill
- [ ] **NOTION-03**: The Skill writes to the channel-patterns Notion page using the **Notion MCP tools** available in the current runtime (local `mcp__notion__*` tools in terminal sessions; the equivalent cloud Notion connector tools in `/schedule` cloud routines)
- [ ] **NOTION-04**: Notion target page resolved via `NOTION_PAGE_ID` env var (in `.env`, gitignored); each run appends a new child page under the parent, titled with the run date
- [ ] **NOTION-05**: Skill renders Notion blocks (headings, callouts for stale-data flags, tables for findings, dividers between sections) that mirror the markdown report — the analyzer never builds Notion blocks itself
- [ ] **NOTION-06**: Skill returns the new child page URL/ID on success, or a structured error on failure; failures do not prevent local artifacts from being saved
- [ ] **NOTION-07**: Skill description and `when_to_use` are precise enough that Claude reliably invokes it when handed a completed analyzer report (test: read the SKILL.md frontmatter in isolation, the trigger should be unambiguous)

### Persistence

- [ ] **PERSIST-01**: Each run writes `reports/{run_date}.md` (run date, not snapshot date) with the same content published to Notion
- [ ] **PERSIST-02**: Each run writes `runs/{run_date}/summary.json` with snapshot dates per table, video count at run time, query row counts, errors, durations, and Notion page URL (if write succeeded)
- [ ] **PERSIST-03**: Local artifacts (`reports/`, `runs/`) are always written even if the Notion write fails — the work is never lost

### Schedule

- [ ] **SCHED-01**: `docs/schedule.md` documents the weekly `/schedule` routine setup for Monday 9am Phoenix time, covering both local (Claude Code on Kyle's machine) and cloud (claude.ai routine) variants
- [ ] **SCHED-02**: The Notion writer Skill works identically in both contexts (local MCP, cloud connector) without code changes

### Error Handling

- [ ] **ERR-01**: Each failure mode (bq auth, missing table, empty table, Notion write fail, env var missing) has a named section in `docs/runbook.md` with recovery steps
- [ ] **ERR-02**: A failed run still writes `summary.json` with the error captured, so the next run can detect a prior failure
- [ ] **ERR-03**: New failure modes encountered during builds get added to `docs/runbook.md` and `CHANGELOG.md` as part of the fix

## v2 Requirements

Deferred until v1 has actually shipped and produced a few real reports.

### Trend Analysis

- **TREND-01**: Week-over-week comparison against the previous `reports/{date}.md`
- **TREND-02**: Pattern-stability tracking (does a "moderate confidence" pattern repeat across runs?)

### Richer Reports

- **RICH-01**: Per-section confidence summary at the top of the report
- **RICH-02**: Embedded mini-charts (sparklines via Notion image upload or ASCII)
- **RICH-03**: Auto-generated "open questions for next week" carried forward into the next run's input context

### Workflow

- **FLOW-01**: `/schedule` routine config checked into the repo (currently lives in the Anthropic UI)
- **FLOW-02**: Pre-commit hook validates new SQL files against the data-contract rules in `BUSINESS_RULES.md`

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web dashboard / frontend | Consumer is Kyle reading Notion; a UI would defeat the "honest analyst" framing |
| Causal inference / experiment design | Analyzer reports correlation and flags hypotheses; it does not claim cause |
| Cross-channel benchmarking | Single channel only; competitor data is not part of the dataset contract |
| Real-time / sub-daily refresh | Weekly cadence is the explicit design point |
| BigQuery ingest / ETL | Upstream pipeline is owned elsewhere; analyzer only reads |
| Python application orchestrator | Rejected in questioning — keep the "AI analyst" feel via CLAUDE.md + bq + SQL |
| BigQuery cost preview / dry-run guards | Dataset is small (~24 videos, ~10k rows); SQL discipline is sufficient |
| Cadence detection (`RUN_WINDOW` env var) | YAGNI; weekly is the design point |
| Direct Notion API client (no MCP) | The Notion MCP tools already work in both local + cloud contexts; adding a second transport doubles maintenance |
| Notion writer as a global skill | Project-local so it ships with the repo and viewers can fork |
| Real-time alerting on data-health flags | Weekly report already surfaces them; paging would be over-engineered |

## Traceability

Each v1 requirement maps to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HEALTH-01 | Phase 1 | Pending |
| HEALTH-02 | Phase 1 | Pending |
| HEALTH-03 | Phase 1 | Pending |
| BQ-01 | Phase 1 | Pending |
| BQ-02 | Phase 1 | Pending |
| BQ-03 | Phase 1 | Pending |
| CSV-01 | Phase 3 | Pending |
| CSV-02 | Phase 3 | Pending |
| ANALYSIS-01 | Phase 2 | Complete |
| ANALYSIS-02 | Phase 2 | Complete |
| ANALYSIS-03 | Phase 2 | Complete |
| ANALYSIS-04 | Phase 2 | Complete |
| ANALYSIS-05 | Phase 2 | Complete |
| REPORT-01 | Phase 2 | Complete |
| REPORT-02 | Phase 2 | Complete |
| REPORT-03 | Phase 2 | Complete |
| NOTION-01 | Phase 1 | Pending |
| NOTION-02 | Phase 1 | Pending |
| NOTION-03 | Phase 1 | Pending |
| NOTION-04 | Phase 1 | Pending |
| NOTION-05 | Phase 1 | Pending |
| NOTION-06 | Phase 1 | Pending |
| NOTION-07 | Phase 1 | Pending |
| PERSIST-01 | Phase 1 | Pending |
| PERSIST-02 | Phase 1 | Pending |
| PERSIST-03 | Phase 1 | Pending |
| SCHED-01 | Phase 3 | Pending |
| SCHED-02 | Phase 3 | Pending |
| ERR-01 | Phase 3 | Pending |
| ERR-02 | Phase 1 | Pending |
| ERR-03 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 31 total
- Mapped to phases: 31 ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-24*
*Last updated: 2026-05-24 after roadmap creation (traceability table populated)*
