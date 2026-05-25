# Phase 1: First Notion Report End-to-End - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-24
**Phase:** 1-First Notion Report End-to-End
**Areas discussed:** Run trigger + orchestration shape (scheduling and BigQuery access folded in mid-discussion)

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Run trigger + orchestration shape | How the operator actually starts a run; entry-point shape and recipe location | ✓ |
| Notion Skill input contract | Strict dict vs freeform markdown handoff to write-notion-report | |
| Phase-1 report depth | How much of the 6-section structure ships in Phase 1 | |
| Notion page model + MCP tool choice | Title format, parent-vs-child layout, exact Notion MCP tool | |

**User's choice:** Run trigger + orchestration shape (only).
**Notes:** The other three areas were deferred to Claude's discretion / planner — see CONTEXT.md → "Claude's Discretion" for the defaults the planner will use unless surfaced as blockers.

---

## Run Trigger + Orchestration Shape

### Q1 — Primary entry point

| Option | Description | Selected |
|--------|-------------|----------|
| Project-local slash command `/run-analyzer` | `.claude/commands/run-analyzer.md` at repo root; `/schedule` calls it; ships with the repo | ✓ |
| RUN.md prompt at repo root | `RUN.md` invoked via `@RUN.md run it`; routine config quotes its content | |
| No new entry point | Operator says something natural; Claude reads `CLAUDE.md` and figures it out | |
| Slash command that wraps RUN.md | Both — command reads `RUN.md` and executes it | |

**User's choice:** Project-local slash command `/run-analyzer`.

### Q2 — What `/run-analyzer` actually does

| Option | Description | Selected |
|--------|-------------|----------|
| Linear recipe in the slash command | Full sequence spelled out in the command file (~80–150 lines) | ✓ |
| Thin entrypoint that defers to CLAUDE.md | Short command file (~20 lines), real logic in `CLAUDE.md` | |
| Stepwise checklist | Numbered step-by-step (10–20 steps); most explicit | |

**User's choice:** Linear recipe in the slash command file.

### Q3 — Where the weekly run fires (introduced after Kyle asked about scheduling + BigQuery MCP)

| Option | Description | Selected |
|--------|-------------|----------|
| Local `/schedule` on your machine | Fires locally; uses `bq` CLI + local Notion MCP | |
| Cloud claude.ai routine | Fires in cloud; uses BigQuery MCP + Notion connector | |
| Both — local primary, cloud as backup | Default local; cloud variant for vacations / laptop-off weeks | ✓ |

**User's choice:** Both — local primary, cloud as backup.
**Notes:** Kyle confirmed the BigQuery MCP is already wired in the cloud context. This is what made the cloud variant viable.

### Q4 — BigQuery access transport

| Option | Description | Selected |
|--------|-------------|----------|
| `bq` CLI primary, MCP fallback | Use `bq query --format=json` when available; fall back to BigQuery MCP otherwise | |
| BigQuery MCP primary everywhere | Use MCP tools in both contexts; remove `bq` CLI dependency from `CLAUDE.md` | |
| Pick per-context: `bq` CLI locally, MCP in cloud | Detect context, route accordingly | ✓ |

**User's choice:** Pick per-context — `bq` CLI locally, BigQuery MCP in cloud.

### Q5 — Context detection mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Probe available tools at runtime | Recipe says "if `bq` available, use it; else use MCP" — Claude decides | ✓ |
| Explicit `--cloud` flag | `/run-analyzer --cloud` from cloud routine | |
| `RUN_CONTEXT` env var | Set `RUN_CONTEXT=local` or `=cloud` | |

**User's choice:** Probe available tools at runtime.

### Q6 — How the cloud routine invokes the same run

| Option | Description | Selected |
|--------|-------------|----------|
| Routine prompt embeds the recipe verbatim | Cloud routine config contains the same instructions as `.claude/commands/run-analyzer.md`; drift risk acknowledged | ✓ |
| Routine prompt says "read the slash command from GitHub" | One-liner that reads via GitHub connector; single source of truth, extra dependency | |
| Defer cloud variant to Phase 3 | Phase 1 ships only the local path; cloud path waits | |

**User's choice:** Routine prompt embeds the recipe verbatim. `docs/schedule.md` (Phase 3) will provide a copy-pasteable version and call out the drift risk.

---

## Wrap

| Option | Description | Selected |
|--------|-------------|----------|
| Wrap and write CONTEXT.md | Six decisions on run trigger is enough; defaults capture the rest | ✓ |
| Discuss Notion Skill input contract | Lock the dict shape vs freeform handoff | |
| Discuss Phase-1 report depth | Decide how much of the 6-section structure ships now | |
| Discuss Notion page model + MCP tool choice | Lock child-page title, parent-vs-child layout, exact MCP tool | |

**User's choice:** Wrap.

---

## Claude's Discretion

The user deferred three gray areas to the planner / researcher with sensible defaults documented in CONTEXT.md:

- **Notion Skill input contract** — default to strict dict with `run_date`, `data_health`, `headline`, `working[]`, `not_working[]`, `patterns[]`, `open_questions[]`, `markdown_body`.
- **Phase-1 report depth** — default to Data Health + Headline + one "What's working" finding from `sql/02_top_full_length_videos.sql`, with the other three sections present but empty-labeled.
- **Notion page model + MCP tool choice** — default to title `"Weekly report — {run_date}"`, parent page accumulates child links, Skill calls `mcp__notion__notion-create-pages` (researcher to confirm exact tool name).

## Deferred Ideas

- Embedded mini-charts in Notion (RICH-02 v2)
- Auto-carrying "open questions" forward into next run's input context (RICH-03 v2)
- Versioning the `/schedule` routine config in the repo (FLOW-01 v2)
- Pre-commit hook validating SQL against `BUSINESS_RULES.md` (FLOW-02 v2)
- BigQuery cost guards (already out of scope per PROJECT.md)
- Cadence detection / `RUN_WINDOW` env var (already out of scope per PROJECT.md)
