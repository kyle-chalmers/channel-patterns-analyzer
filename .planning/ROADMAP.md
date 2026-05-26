# Roadmap: Channel Patterns Analyzer

**Created:** 2026-05-24
**Granularity:** coarse
**Mode:** Vertical MVP — every phase delivers an end-to-end runnable analyzer slice
**Coverage:** 31/31 v1 requirements mapped

## Phases

- [x] **Phase 1: First Notion Report End-to-End** — Smallest viable analyzer run: data-health check + one BigQuery pull + minimal report + `write-notion-report` Skill produces a real child page on the channel-patterns Notion page (completed 2026-05-25)
- [x] **Phase 2: Honest Analyst Depth** — Age control, small-sample hedging, six-section structure, prior-report calibration, and voice rules applied so the published report meets the CLAUDE.md bar (completed 2026-05-25)
- [ ] **Phase 3: CSV Parity and Operational Polish** — `DATA_SOURCE=csv` reaches feature parity, weekly `/schedule` routine documented for local + cloud, runbook covers every failure mode encountered during the build

## Phase Details

### Phase 1: First Notion Report End-to-End

**Goal:** A single command-driven Claude Code session pulls real BigQuery data, writes a minimal but correctly-structured report to disk, and publishes a child page on the channel-patterns Notion page via a new project-local Skill.
**Mode:** mvp
**Depends on:** Nothing (first phase; scaffold + BigQuery auth + Notion connectivity already verified)
**Requirements:** HEALTH-01, HEALTH-02, HEALTH-03, BQ-01, BQ-02, BQ-03, NOTION-01, NOTION-02, NOTION-03, NOTION-04, NOTION-05, NOTION-06, NOTION-07, PERSIST-01, PERSIST-02, PERSIST-03, ERR-02
**Success Criteria** (what must be TRUE):

  1. Operator can run the analyzer and a new child page appears under the channel-patterns Notion page within 60 seconds, titled with the run date
  2. The published page leads with a Data Health section that names the snapshot date of every analytics table and flags any table older than 3 days in America/Phoenix
  3. Every canonical SQL file executed during the run writes a JSON result dump to `runs/{run_date}/queries/{query_name}.json`, and `runs/{run_date}/summary.json` records snapshot dates, row counts, durations, and the Notion page URL
  4. If the Notion write fails or env vars are missing, `reports/{run_date}.md` and `runs/{run_date}/summary.json` are still written, the failure is captured in `summary.json`, and the operator sees an actionable error mapped to `docs/runbook.md`
  5. Reading `.claude/skills/write-notion-report/SKILL.md` frontmatter in isolation, Claude knows to invoke the Skill when handed a completed analyzer report dictionary**Plans:** 4/4 plans complete

**Wave 1**

- [x] 01-01-PLAN.md — Wave-0 probes (BigQuery MCP + Notion fetch) and scaffold fixups (Phoenix timezone in sql/02/03/04, runbook §5/§6 cross-refs, .gitignore Skill negation, CONTEXT env-var name, runs/README transport+notion_url schema)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Build .claude/skills/write-notion-report/SKILL.md (frontmatter + input contract + Notion block rendering + structured-dict return)
- [x] 01-03-PLAN.md — Build .claude/commands/run-analyzer.md recipe (linear 80–150 lines: preflight, transport probe, data-health + top-videos queries, report draft, Skill invocation, summary.json with try/finally)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-04-PLAN.md — Live end-to-end run + forced-failure run; align docs/runbook.md section names with recipe operator messages; CHANGELOG milestone entry

### Phase 2: Honest Analyst Depth

**Goal:** The report's analytical body satisfies the CLAUDE.md and BUSINESS_RULES.md contract — age-controlled comparisons, confidence-labelled claims, six-section structure, voice rules, prior-report calibration — so Kyle would publish what comes out without rewriting it.
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** ANALYSIS-01, ANALYSIS-02, ANALYSIS-03, ANALYSIS-04, ANALYSIS-05, REPORT-01, REPORT-02, REPORT-03
**Success Criteria** (what must be TRUE):

  1. Every "top performer" or pattern claim in the report excludes videos with `days_since_published < 14`, and cross-age comparisons use a first-30-day window or a labeled views-per-day proxy
  2. Every pattern claim carries a confidence label (low / moderate / standard) in plain sight next to the claim, derived from a live `video_metadata` count queried that run, not a hardcoded number
  3. Published reports contain the six required sections in order (Data Health, Headline, What is working, What is not working, Patterns worth watching, Open questions), with findings showing numbers, age context, and confidence labels inline
  4. Before drafting, the analyzer reads the three most recent `reports/{date}.md` files and uses them to calibrate confidence and avoid restating prior findings verbatim
  5. Report prose passes the voice rules — no em dashes, none of the banned vocabulary, no formulaic openers or closers, first-person plural where it fits

**Plans:** 3/3 plans complete
**Wave 1**

- [x] 02-01-PLAN.md — Fix sql/02, sql/03, sql/04 (Phoenix tz + latest-common-snapshot CTE + remove LIMIT 20) per D-05; verify Phase 1 dependency assumptions

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Extend /run-analyzer recipe with prior-report read step, eligible-count step, and reworked draft step (six sections, inline confidence labels, stale-table disclaimers)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-03-PLAN.md — Insert self-audit step (D-01 Layer 2) between draft and publish; extend summary.json schema with voice_audit

### Phase 3: CSV Parity and Operational Polish

**Goal:** The analyzer runs end-to-end against `DATA_SOURCE=csv` with identical behavior to the BigQuery path, the weekly Monday 9am Phoenix `/schedule` routine is documented for both local and cloud variants, and every failure mode hit during builds is captured in the runbook so future runs degrade visibly rather than silently.
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** CSV-01, CSV-02, SCHED-01, SCHED-02, ERR-01, ERR-03
**Success Criteria** (what must be TRUE):

  1. Setting `DATA_SOURCE=csv` and running the analyzer produces a structurally identical report (same six sections, same confidence labels, same persistence artifacts) — only the data-health timestamps differ from the BigQuery path
  2. Every SQL-driven step in the BigQuery path has a documented CSV-backed equivalent reading from `sample_data/*.csv` — no analyzer behavior is BigQuery-only
  3. `docs/schedule.md` walks an operator through setting up the weekly Monday 9am Phoenix `/schedule` routine in both local (Claude Code terminal) and cloud (claude.ai routine) variants, and the `write-notion-report` Skill works identically in both contexts without code changes
  4. `docs/runbook.md` contains a named recovery section for each failure mode (bq auth, missing table, empty table, Notion write fail, missing env var), and any new failure mode encountered during the build is added there plus logged in `CHANGELOG.md` as part of the fix

**Plans:** TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. First Notion Report End-to-End | 4/4 | Complete   | 2026-05-25 |
| 2. Honest Analyst Depth | 3/3 | Complete    | 2026-05-26 |
| 3. CSV Parity and Operational Polish | 0/0 | Not started | - |

## Coverage Summary

All 31 v1 requirements mapped to exactly one phase. See REQUIREMENTS.md traceability table for the mapping.

| Phase | Requirement Count | Requirements |
|-------|-------------------|--------------|
| 1 | 17 | HEALTH-01, HEALTH-02, HEALTH-03, BQ-01, BQ-02, BQ-03, NOTION-01..07, PERSIST-01, PERSIST-02, PERSIST-03, ERR-02 |
| 2 | 8 | ANALYSIS-01..05, REPORT-01, REPORT-02, REPORT-03 |
| 3 | 6 | CSV-01, CSV-02, SCHED-01, SCHED-02, ERR-01, ERR-03 |

**Design notes:**

- ERR-02 (failed runs still write `summary.json` with the error) sits in Phase 1 because it is the minimum survivability behavior the smallest viable run needs. ERR-01 (named runbook sections for every failure mode) and ERR-03 (newly-encountered failure modes captured in runbook + CHANGELOG) live in Phase 3 because they consolidate what the prior two phases surfaced.
- Phase 1 bundles every NOTION requirement together. The Skill is small enough to build in one pass, and partial Notion support would leave the analyzer in a non-runnable state — violating Vertical MVP framing.
- The age-control and small-sample SQL patterns already exist in `sql/02_top_full_length_videos.sql` and `sql/03_age_controlled_performance.sql`. Phase 2 wires those into the analyzer's reasoning and report draft, rather than rewriting the SQL.

---
*Roadmap created: 2026-05-24*
*Phase 1 plans created: 2026-05-25*
