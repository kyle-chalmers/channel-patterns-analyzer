# Wave-0 probe notes (Phase 1)

Probed: 2026-05-25 (TEMPLATE — see "Operator action required" below)
Probed by: <operator to fill in once probes are run>

> **Operator action required.** This file was scaffolded by the Plan 01-01
> executor agent. The executor session did not have the
> `mcp__claude_ai_Google_Cloud_BigQuery__*` or `mcp__claude_ai_Notion__*` tools
> loaded (only Microsoft Learn and Zapier MCPs were attached), so the two live
> probes could not be performed during automated execution. Plans 02 and 03
> depend on the recorded argument shapes below. Before running Plan 02 or
> Plan 03, run both probes in a Claude Code session that has the BigQuery and
> Notion MCPs attached, and paste the raw outputs into the placeholder blocks
> below. The plan's checkpoint resume-signal is "approved" once both blocks
> have real outputs.

## BigQuery MCP — execute_sql_readonly

- Tool name: `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly`
- Test query: `SELECT 1 AS one, 'hello' AS label`
- Argument key for SQL: `<"sql" or "query" or other — fill from live probe>`
- Argument key for project: `<"project_id" or "project" or "n/a" — fill from live probe>`
- Response shape (paste the raw response):

  ```
  <paste raw MCP response here, including row structure and field-key names>
  ```

- Error if project omitted: `<verbatim error from a second probe call without project_id, or "not tested">`
- Standard SQL handling: `<does the tool require an explicit dialect flag, or accept standard SQL by default? — fill from live probe>`

### Research baseline (from 01-RESEARCH.md §4)

RESEARCH §4 documents the expected shape as
`{ "sql": "<SELECT ...>", "project_id": "<optional>" }`, returning result rows
as a structured response. The recipe in Plan 03 will encode whichever shape the
live probe confirms.

## Notion MCP — notion-fetch against NOTION_REPORT_PAGE_ID

- Tool name: `mcp__claude_ai_Notion__notion-fetch`
- Env var: `NOTION_REPORT_PAGE_ID` (value not recorded for hygiene — only record
  "set / not set" and the parent page title returned)
- Env var status at probe time: `<"set" or "not set" — fill from live probe>`
- Fetch result (paste the parent page object METADATA only, not the full body):

  ```
  <paste page object metadata: id, title, parent type, last_edited_time, etc.>
  ```

- Parent page title: `<title from response — should match the channel-patterns page>`
- UUID form accepted: `<"dashed" / "undashed" / "both" — try one then the other; record what each returned>`
- Integration permissions visible from the response: `<note whether the integration has read+update access; flag any missing permission>`
- Notes / failure modes encountered:

  `<free text — record any 404 / permission_denied / transport errors here so Plan 03's recipe matches the right error pattern>`

### Research baseline (from 01-RESEARCH.md §2)

RESEARCH §2 documents `notion-fetch` as a wrapper around the Notion REST GET
page endpoint. The REST API accepts both dashed and undashed UUIDs; the MCP
wrapper may be stricter. The probe pins down which form the wrapper accepts so
the Skill (Plan 02) can normalize before the create call.

## What Plans 02 and 03 read from this file

- **Plan 02 (write-notion-report Skill):** uses the `notion-fetch` argument
  shape and UUID-form requirement to write the page-preflight check inside the
  Skill.
- **Plan 03 (`/run-analyzer` recipe):** uses the `execute_sql_readonly`
  argument keys to wire the cloud-transport branch (`TRANSPORT=bq_mcp`).

If either probe block remains unfilled when Plans 02/03 begin, those plans
should halt at their first MCP-invocation step until the probe is completed.
