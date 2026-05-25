# Phase 3: CSV Parity and Operational Polish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-25
**Phase:** 3-CSV Parity and Operational Polish
**Areas discussed:** Schedule docs scope (cloud-routine launch)

**Session context:** Phase 1 was mid-research and Phase 2 had not started when this discussion ran. The user chose to capture Phase 3 context ahead of Phase 1 execution to surface scheduling decisions early. Hard ordering constraint (Phase 1 must ship `.claude/commands/run-analyzer.md` before Phase 3 work begins) is recorded in CONTEXT.md.

---

## Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| CSV execution engine | DuckDB vs pandas vs sqlite for running the same SQL against CSV fixtures | |
| CSV freshness behavior | Sample CSVs always have today's date — leave fresh, regenerate per-run, or ship a stale fixture set | |
| Schedule docs scope | Polishing docs/schedule.md and getting the cloud routine actually launchable | ✓ |
| Runbook expansion mechanism | How Phase 3 captures failure modes hit during Phase 1+2 into docs/runbook.md | |

**User's choice:** Schedule docs scope, with stated intent: "I want to make sure that the schedule is super ironed out and that we can launch this as a routine in the web." Reframed the area from doc polish to cloud-routine launchability.

---

## Schedule docs scope — Cloud BQ auth

| Option | Description | Selected |
|--------|-------------|----------|
| BigQuery web connector (Recommended) | Auth BQ as a connector in the Anthropic account, same as Notion. No secrets in routine env vars, no SA key rotation. | ✓ |
| Service account JSON in env var | Paste full SA JSON into routine env var; recipe writes to disk before BQ calls. More moving parts. | |
| You decide | Defer to researcher. | |

**User's choice:** BigQuery web connector.
**Notes:** User followed up with confirmation: "I do have the BigQuery MCP set up in Claude on the web." Promoted "BigQuery MCP available in cloud routine" from research-task to confirmed-fact, captured in CONTEXT.md `<specifics>`.

---

## Schedule docs scope — Recipe source

| Option | Description | Selected |
|--------|-------------|----------|
| Slash command IS canonical; docs say 'paste this file' (Recommended) | `.claude/commands/run-analyzer.md` is single source of truth. Zero drift. | ✓ |
| Separate routines/cloud-system-prompt.md file | Dedicated file under routines/ holds cloud-formatted recipe. More flexibility, more drift risk. | |
| Inline the recipe inside docs/schedule.md | Verbatim block in a fenced code block alongside setup. Third place to keep in sync. | |

**User's choice:** Slash command is canonical.
**Notes:** Requires Phase 1's slash command to stay self-contained enough for copy-paste (no project-local @-imports the cloud context can't resolve). Already a Phase 1 D-06 requirement; Phase 3 verifies it.

---

## Schedule docs scope — Smoke test

| Option | Description | Selected |
|--------|-------------|----------|
| Run-now checklist in docs (Recommended) | schedule.md ends with verify-the-routine-works checklist (Notion page, six sections, summary.json, UI shows completed). Failures link to runbook sections. | ✓ |
| Test-mode flag in the recipe | ROUTINE_TEST_MODE env var routes to NOTION_TEST_PAGE_ID. More env var surface area. | |
| First Monday is the smoke test | Trust the routine, watch Monday, fix on failure. Lowest setup cost. | |

**User's choice:** Run-now checklist in docs.
**Notes:** Mid-question user noted "We have not executed phase one yet, so that's probably what's missing." Hard ordering constraint captured in CONTEXT.md.

---

## Schedule docs scope — Doc fidelity

| Option | Description | Selected |
|--------|-------------|----------|
| Step-by-step UI walkthrough with field names (Recommended) | Explicit numbered steps with claude.com field labels and values. Concrete; UI labels rot over time but accepted with a CHANGELOG note. | ✓ |
| Invariants checklist (what must be true) | Skip UI clicks; enumerate config requirements. More durable but riskier for first-time setup. | |
| Walkthrough plus invariants | Both. Most thorough, longest doc, most maintenance. | |

**User's choice:** Step-by-step UI walkthrough with field names.
**Notes:** Matches the stated goal of "ironed out so we can launch this as a routine in the web." Operator should be able to follow the doc top-to-bottom and produce a working routine on the first try.

---

## Continue or move on?

| Option | Description | Selected |
|--------|-------------|----------|
| I'm ready for context | Lock current decisions; let planner pick defaults for CSV and runbook from the requirements. | ✓ |
| Move to CSV execution engine | Discuss DuckDB vs pandas vs sqlite. | |
| More questions about Schedule | Keep digging on env-var inventory, failure visibility, local /schedule coverage. | |
| Move to Runbook expansion | Discuss how Phase 3 captures Phase 1+2 failure modes. | |

**User's choice:** I'm ready for context.
**Notes:** CSV execution engine, CSV freshness behavior, CSV parity definition, ERR-01 runbook coverage, and ERR-03 update mechanism are explicitly handed to the planner with defaults documented in CONTEXT.md `<decisions>` § Claude's Discretion.

---

## Claude's Discretion

Recorded in CONTEXT.md `<decisions>` § Claude's Discretion. Summary:
- CSV execution: stdlib Python helper returning `bq query --format=json`-shaped JSON; not DuckDB.
- CSV freshness: regenerate per CSV-mode run; `--snapshot-date` arg for stale-path testing.
- CSV parity: "structurally identical" = same six sections, same labels, same artifacts; not identical findings text.
- ERR-01: schedule.md Run-now checklist drives runbook expansion; explicit inventory of cloud-side failure sections.
- ERR-03: manual discipline backed by maintenance doc; no automated tooling.

## Deferred Ideas

Recorded in CONTEXT.md `<deferred>`. Summary:
- CSV execution engine deep-dive (re-open if research surfaces strong DuckDB case)
- CSV freshness as a test harness (Phase 4 / v2)
- Test-mode env var for routine smoke-testing (revisit if smoke tests become routine)
- Versioning routine_config.json in the repo (FLOW-01, v2)
- End-of-phase forensics pass for runbook coverage (rejected — manual discipline sufficient)
