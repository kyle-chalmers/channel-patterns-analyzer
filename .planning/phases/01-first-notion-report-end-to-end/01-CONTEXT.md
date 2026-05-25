# Phase 1: First Notion Report End-to-End - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning

<domain>
## Phase Boundary

A Claude Code session that pulls real BigQuery data, drafts a minimal but correctly-structured report, and publishes a child page on the channel-patterns Notion page via a new project-local `write-notion-report` Skill. Phase 1 covers everything from "operator triggers a run" through "Notion page exists, local artifacts written." Voice/age-control/six-section analytical depth is Phase 2. CSV parity and full schedule documentation is Phase 3.

In-scope this phase: HEALTH-01..03, BQ-01..03, NOTION-01..07, PERSIST-01..03, ERR-02 (17 requirements). Out-of-scope: ANALYSIS-*, REPORT-*, CSV-*, SCHED-* (Phase 1 may stub these but must not block Phase 1 success criteria on them), SCHED-* and full ERR-01/03 (Phase 3).

</domain>

<decisions>
## Implementation Decisions

### Run Trigger and Orchestration

- **D-01: Entry point is a project-local slash command `/run-analyzer`** at `.claude/commands/run-analyzer.md`. The file is committed to the repo so viewers/forkers see exactly how a run executes. (Note: the project's `.gitignore` currently excludes `.claude/skills/`; the slash command lives in `.claude/commands/` and may need an explicit un-ignore or whitelist depending on the current `.gitignore` patterns.)
- **D-02: The slash command file is a linear recipe** (~80–150 lines of markdown) that spells out the full sequence: data-health query → fail-fast on stale → pull canonical SQL files via the appropriate transport → write JSON dumps to `runs/{date}/queries/` → draft minimal report → invoke `write-notion-report` Skill → save `reports/{date}.md` and `runs/{date}/summary.json`. Predictable for viewers reading the file on GitHub; planner should not split this into multiple files.
- **D-03: Context detection is "probe available tools at runtime"** — no `--cloud` flag, no `RUN_CONTEXT` env var. The recipe starts with: "If the `bq` CLI is available, use it. Otherwise, use the BigQuery MCP tools." Claude makes the call at runtime based on which tools are loaded in the session.
- **D-04: BigQuery access is context-aware** — `bq` CLI when running locally (preserves the current `CLAUDE.md` / README setup), BigQuery MCP tools when running in a cloud routine where the CLI isn't available. The recipe documents both paths; the SQL files themselves are unchanged (canonical SQL is portable across transports).
- **D-05: Schedule host is "both, with local primary"** — Claude Code's local `/schedule` is the default weekly fire; a claude.ai cloud routine exists as a backup for vacations / laptop-off weeks. Phase 1 must produce an analyzer flow that runs cleanly in both contexts. Phase 3 (SCHED-01/02) handles the documentation polish; Phase 1 just needs to avoid baking in any local-only assumption that would break the cloud variant later.
- **D-06: Cloud-routine invocation embeds the recipe verbatim** — claude.ai cloud routines cannot call project-local slash commands. The routine config in claude.ai contains the same instructions as `.claude/commands/run-analyzer.md`. `docs/schedule.md` (Phase 3) provides a copy-pasteable version and documents the drift risk. Phase 1 should keep the recipe self-contained enough that copy-paste-into-routine is realistic (no project-local @-imports the cloud context can't resolve).

### Claude's Discretion (gray areas the user deferred to planner / researcher)

The user opted to discuss only the run-trigger area; the following are open for the planner and researcher to resolve with sensible defaults:

- **Notion Skill input contract (NOTION-02).** Default to a **strict dict** with keys (`run_date`, `data_health`, `headline`, `working[]`, `not_working[]`, `patterns[]`, `open_questions[]`, `markdown_body`). Rationale: strict shape is more testable and makes Notion block rendering deterministic. Planner may revise if the researcher surfaces a cleaner contract from Claude Code Skill conventions.
- **Phase-1 report depth.** Default to **Data Health + Headline + one "What's working" finding** sourced from `sql/02_top_full_length_videos.sql`. Enough content to prove end-to-end (≥3 sections) without dragging Phase 2's analytical work into Phase 1. The other report sections (What's not working, Patterns, Open questions) may be empty placeholders in Phase 1 — clearly labeled as such, not silently omitted.
- **Notion page model + MCP tool choice.** Default to: title format `"Weekly report — {run_date}"`; each run appends a child page under the parent referenced by `NOTION_REPORT_PAGE_ID`; parent page accumulates a running list of child links (no summary table in Phase 1). Skill calls `mcp__notion__notion-create-pages` (or the equivalent cloud-connector tool) with the parent ref from `NOTION_REPORT_PAGE_ID`. Researcher should verify the exact tool name and parent-ref shape against the Notion MCP currently installed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Analyzer runtime contract
- `CLAUDE.md` — Analyzer voice, reasoning rules, age control, sample-size thresholds, report structure, persistent-structure rules. This is the executable contract.
- `BUSINESS_RULES.md` — Fiscal calendar, exclusions, data refresh expectations, per-table grain, join keys. `@`-imported by `CLAUDE.md`.

### Requirements and scope
- `.planning/PROJECT.md` — Project framing, validated vs active requirements, key decisions log, constraints.
- `.planning/REQUIREMENTS.md` — 31 v1 requirements with REQ-IDs; Phase 1 covers 17 of them (see traceability table).
- `.planning/ROADMAP.md` §"Phase 1: First Notion Report End-to-End" — phase goal, requirements, success criteria.

### SQL pattern library (already shipped)
- `sql/01_latest_snapshot_overview.sql` — One-row health check across `video_metadata` + `daily_video_stats`.
- `sql/02_top_full_length_videos.sql` — Top full-length videos by views (likely source for Phase 1's first "What's working" finding).
- `sql/03_age_controlled_performance.sql` — Age-normalized comparison patterns (Phase 2 wiring, not Phase 1).
- `sql/04_data_health_check.sql` — Per-table `MAX(snapshot_date)` + `days_stale`. **This is the literal first query of every run.** Note: the file currently uses `CURRENT_DATE()` (UTC); the rule in `BUSINESS_RULES.md` §3 is `CURRENT_DATE('America/Phoenix')`. Planner must reconcile.

### Persistence schemas (already shipped)
- `runs/README.md` — `summary.json` schema, folder layout, what each file means.
- `reports/README.md` — Naming convention (run date, not snapshot date), how the analyzer reads prior reports.
- `docs/runbook.md` — Failure-mode playbook. Phase 1 must surface bq-auth and Notion-write failures with actionable messages that map here.

### Tool/integration context
- `.env.example` — Existing env-var template. Phase 1 adds `NOTION_REPORT_PAGE_ID` to it.
- `README.md` §3.1–3.6 — gcloud + bq CLI setup walkthrough (already shipped). Phase 1 may need to add a Notion-side equivalent section.
- `.planning/codebase/STRUCTURE.md` — Directory layout, where new files belong.
- `.planning/codebase/STACK.md` — Confirms bq CLI + Claude Code Skill stack; Notion MCP is the handoff transport.

### External / runtime
- Notion MCP tools available in this Claude Code session: `mcp__claude_ai_Notion__notion-create-pages`, `notion-update-page`, `notion-fetch`, `notion-search` (full list is broader; researcher should confirm which one is the right primitive for "append child page under parent").
- BigQuery MCP (Kyle confirmed connected). Researcher should identify the exact tool names and the SQL-execution primitive (likely something like `mcp__bigquery__run_query` or similar — depends on which BigQuery MCP server is installed).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`sql/04_data_health_check.sql`** — Ready-to-execute data-health query. Phase 1 just runs it, parses the JSON output, and renders the Data Health section from the result. No new SQL needed for HEALTH-01..03.
- **`sql/02_top_full_length_videos.sql`** — Existing top-videos query is the natural source for Phase 1's single "What's working" finding (per the default report-depth decision).
- **`runs/README.md` `summary.json` schema** — Already specifies the exact shape (`snapshot_dates`, `stale_tables`, `queries_run`, etc.). Phase 1 writes against this schema; planner should not reinvent it.
- **`reports/README.md` naming + analyzer-memory rules** — Already states run-date-not-snapshot-date naming and "read most recent 3–4 reports before drafting" (Phase 2 will exercise the read; Phase 1 establishes the write).

### Established Patterns
- **`@`-imports in `CLAUDE.md`** — `CLAUDE.md` already `@BUSINESS_RULES.md`s. The `/run-analyzer` slash command file can use the same pattern (`@CLAUDE.md`, `@BUSINESS_RULES.md`) to inherit the analyzer contract without re-stating it. This keeps the slash command focused on orchestration, not analysis rules.
- **Bare `youtube_analytics.<table>` references in SQL** — The SQL files do not template the dataset name; the recipe needs to either `sed`-substitute `$BQ_DATASET` before execution, or document that the user must edit the SQL files if their dataset differs. Decision deferred to planner; current default is sed-substitute.
- **`.internal/` for sensitive content, `.env` for runtime config** — Notion page ID is runtime config (goes in `.env`), not sensitive recording notes. Pattern is established.

### Integration Points
- **Slash command → SQL files:** `.claude/commands/run-analyzer.md` references `sql/*.sql` by relative path.
- **Slash command → `write-notion-report` Skill:** Slash command's final step is "invoke the `write-notion-report` Skill with the assembled report dictionary." Skill lives at `.claude/skills/write-notion-report/SKILL.md` (project-local, committed).
- **`write-notion-report` Skill → Notion MCP tools:** Skill calls whichever Notion MCP tool is available in the runtime (local terminal Notion MCP or cloud claude.ai Notion connector — both expose compatible tool surfaces).
- **Failure surfacing:** All failure paths write to `runs/{date}/summary.json` with an `errors[]` field per `runs/README.md`, then surface a one-line operator message that points to a `docs/runbook.md` section.

</code_context>

<specifics>
## Specific Ideas

- **Kyle specifically called out the BigQuery MCP connection** during discussion. Researcher should confirm which BigQuery MCP server is installed (Google's official, a community fork, etc.) and document the exact tool surface in CONTEXT.md or RESEARCH.md so the slash command's "cloud path" branch is concrete rather than aspirational.
- **The 89-day-stale `daily_video_analytics` table** (observed at planning time on 2026-05-24) is the natural first-run integration test: the Data Health section should flag it, and the rest of the report should explicitly disclaim that traffic-source / watch-time findings are unavailable. Don't fake it.
- **The slash command's recipe should explicitly forbid silent fallback** — if BigQuery is unreachable AND `DATA_SOURCE=csv` isn't set, the run must stop and surface the error, not fall back to CSV without permission. Matches `CLAUDE.md` §"When something blocks the run."

</specifics>

<deferred>
## Deferred Ideas

- **Embedded mini-charts in Notion** (sparklines or ASCII visualizations) — captured as RICH-02 in REQUIREMENTS.md v2. Not Phase 1.
- **Auto-carrying "open questions" forward into the next run's input** — captured as RICH-03 in REQUIREMENTS.md v2.
- **`/schedule` routine config checked into the repo** — captured as FLOW-01 in REQUIREMENTS.md v2. Phase 3 documents the setup in `docs/schedule.md` but does not version-control the routine config itself.
- **Pre-commit hook validating new SQL files against `BUSINESS_RULES.md`** — captured as FLOW-02 in REQUIREMENTS.md v2.
- **Cost guards on BigQuery queries (`--maximum_bytes_billed`)** — explicitly out of scope per PROJECT.md; revisit if dataset grows 10×+.
- **Cadence detection / `RUN_WINDOW` env var** — explicitly out of scope; weekly is the design point.

</deferred>

---

*Phase: 1-First Notion Report End-to-End*
*Context gathered: 2026-05-24*
