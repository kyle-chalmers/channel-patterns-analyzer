# Wave-0 probe notes (Phase 1)

Probed: 2026-05-25
Probed by: orchestrator session (Claude Code) with `mcp__claude_ai_Google_Cloud_BigQuery__*` and `mcp__claude_ai_Notion__*` MCPs attached

> Probes completed. The Plan 01-01 executor agent's session did not have the
> required MCPs attached, so the orchestrator session ran both probes after the
> executor finished. Plans 02 and 03 should treat the argument shapes recorded
> below as authoritative for the cloud-transport branch.

## BigQuery MCP — execute_sql_readonly

- Tool name: `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly`
- Test query: `SELECT 1 AS one, 'hello' AS label`
- Argument key for SQL: `query` (NOT `sql`; RESEARCH §4's hypothesis was wrong)
- Argument key for project: `projectId` (camelCase, NOT `project_id`; RESEARCH §4's hypothesis was wrong)
- Both `projectId` and `query` are REQUIRED by the tool schema — the MCP wrapper does NOT fall back to the active `gcloud config` project. Omitting `projectId` produces a tool-schema validation error before the call reaches BigQuery.
- Response shape (live response, paths preserved):

  ```json
  {
    "jobComplete": true,
    "queryId": "job_ptf8InC_Yx3QE3Xmwz7zFS3B1-G3",
    "rows": [
      {"f": [{"v": "1"}, {"v": "hello"}]}
    ],
    "schema": {
      "fields": [
        {"mode": "NULLABLE", "name": "one", "type": "INTEGER"},
        {"mode": "NULLABLE", "name": "label", "type": "STRING"}
      ]
    },
    "totalBytesBilled": "0",
    "totalBytesProcessed": "0",
    "totalSlotMs": "9"
  }
  ```

- **KEY FINDING:** rows use the BigQuery REST `{f: [{v: ...}, ...]}` positional shape — NOT named keys. The recipe in Plan 03 must zip each row's `f` array against `schema.fields[].name` to recover column names. This differs from the `bq query --format=json` CLI output, which returns named-key objects. Skill (Plan 02) does not handle BigQuery rows so this only matters for the analyzer recipe.
- Number-like fields (`totalBytesBilled`, `totalBytesProcessed`) come back as JSON strings, not integers — the recipe should coerce to int before any arithmetic.
- Error if project omitted: not tested as a runtime call (the tool schema rejects it client-side before the BigQuery call). Treat `projectId` as mandatory in all invocations.
- Standard SQL handling: accepts standard GoogleSQL by default — no explicit `useLegacySql=false` or dialect flag needed in the tool args.

### Research baseline (from 01-RESEARCH.md §4)

RESEARCH §4 documented the expected shape as `{ "sql": "<SELECT ...>", "project_id": "<optional>" }`. The live probe found `{ "query": "<SELECT ...>", "projectId": "<required>" }` instead. Plan 03's recipe must use the verified shape. Update RESEARCH §4 if it becomes a recurring confusion point.

## Notion MCP — notion-fetch against NOTION_REPORT_PAGE_ID

- Tool name: `mcp__claude_ai_Notion__notion-fetch`
- Env var: `NOTION_REPORT_PAGE_ID` (value not recorded in this file for hygiene per T-01-01 — only "set" status and the parent page title are recorded)
- Env var status at probe time: set in `.env` (gitignored)
- Parent page setup: The "Channel Patterns" page did not exist at probe time. Created it as a child of the existing 🎬 "Content Creation" hub page (parent UUID undashed: `305ccd05494580c9a770f4887a67f508`) before probing. The probe target is the newly created page.
- Fetch result (page object metadata only — NOT body, NOT env value):

  ```json
  {
    "metadata": {"type": "page"},
    "title": "📈 Channel Patterns",
    "url": "https://www.notion.so/<page-id-omitted>",
    "ancestor_path": [
      {"parent-page": {"title": "Content Creation"}}
    ],
    "properties": {"title": "Channel Patterns"}
  }
  ```

- Parent page title (returned from fetch): `Content Creation` — matches expected channel-patterns parent hub.
- UUID form accepted: **both** — dashed (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) and undashed (`xxxxxxxx...`) return byte-identical responses. The MCP wrapper normalizes both forms internally, so the Skill (Plan 02) does NOT need to pre-normalize before calling `notion-fetch`. The Skill SHOULD still document the supported forms for operators reading the runbook.
- Response shape note: response wraps the markdown body inside a `text` field that contains literal `<page>`, `<ancestor-path>`, `<properties>`, `<content>` tags rendered as Notion-flavored markdown. Plan 02's preflight check should treat a successful `notion-fetch` (no error key, `metadata.type == "page"`) as sufficient evidence the page is reachable; it does NOT need to parse the markdown body.
- Integration permissions visible from the response: read access confirmed. Write access not exercised by `notion-fetch`; Plan 02 will exercise it via `notion-create-pages` and surface the actual permission error if write is missing.
- Notes / failure modes encountered: none. Both probe calls returned cleanly. No 404, no permission_denied, no transport errors.

### Research baseline (from 01-RESEARCH.md §2)

RESEARCH §2 documents `notion-fetch` as a wrapper around the Notion REST GET page endpoint. The REST API accepts both UUID forms; the live probe confirms the MCP wrapper also accepts both. Plan 02's Skill therefore does not need a UUID-normalization helper; it can pass the raw env-var value straight through.

## What Plans 02 and 03 read from this file

- **Plan 02 (write-notion-report Skill):** uses the `notion-fetch` argument shape and "both UUID forms accepted" finding to write the page-preflight check inside the Skill. The Skill's preflight is a `notion-fetch` call against `NOTION_REPORT_PAGE_ID`; if it returns metadata.type == "page", proceed; otherwise surface the error with the operator-facing message from `docs/runbook.md`.
- **Plan 03 (`/run-analyzer` recipe):** uses the `execute_sql_readonly` argument keys (`projectId`, `query`) and the row-shape finding (positional `f[].v` arrays zipped against `schema.fields[].name`) to wire the cloud-transport branch (`TRANSPORT=bq_mcp`). The recipe must also coerce string-typed byte counts to integers if any cost-discipline check needs arithmetic.
