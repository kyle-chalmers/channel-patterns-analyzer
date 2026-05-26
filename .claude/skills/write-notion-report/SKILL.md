---
name: write-notion-report
description: Publishes the analyzer's weekly channel-patterns report to Notion as a new child page. Invoke this whenever the analyzer has assembled a completed report dictionary (keys, run_date, data_health, headline, working, not_working, patterns, open_questions, markdown_body) and is ready to publish. The analyzer never writes Notion blocks itself; it hands the dict to this skill.
when_to_use: Trigger phrases, "publish the report to Notion", "write the weekly report", "send the analyzer output to Notion", "hand the assembled report dict to write-notion-report".
disable-model-invocation: false
allowed-tools: mcp__claude_ai_Notion__notion-create-pages mcp__claude_ai_Notion__notion-fetch
---

# write-notion-report

Publish the analyzer's weekly channel-patterns report to Notion as a new child page under the configured parent. This Skill is the only component in the project that touches Notion. The analyzer (the `/run-analyzer` recipe) assembles a structured report dictionary and hands it here; rendering Notion blocks, calling the MCP, classifying errors, and returning a structured result are this Skill's job.

## Input contract

The caller MUST pass a single dictionary with the eight keys below. If any required key is missing or the wrong type, return `{ "ok": false, "error": "input dict missing required key: <name>", "category": "input_invalid" }` and do NOT attempt the Notion call.

| Key | Type | Required | Description |
|---|---|---|---|
| `run_date` | string `YYYY-MM-DD` | yes | Run date in Phoenix time. Matches the `reports/{run_date}.md` filename and the title used for the new Notion child page. |
| `data_health` | dict | yes | Shape: `{ "snapshot_dates": { <table>: <YYYY-MM-DD>, ... }, "stale_tables": [<string>, ...] }`. The `stale_tables` entries are human-readable strings like `"daily_video_analytics (89 days)"` and render as callout blocks in the Data Health section. |
| `headline` | string | yes | One or two sentences. Empty string is allowed only when `data_health.stale_tables` is non-empty and the headline is essentially "data is stale". |
| `working` | list of dict | yes (may be empty) | Each entry: `{ "title": <string>, "body": <string>, "confidence": "low" \| "moderate" \| "standard" }`. Reserved for Phase 2 enrichment; Phase 1 renders from `markdown_body` only. |
| `not_working` | list of dict | yes (may be empty) | Same shape as `working`. |
| `patterns` | list of dict | yes (may be empty) | Same shape as `working`. |
| `open_questions` | list of string | yes (may be empty) | Plain bullets. |
| `markdown_body` | string | yes | The full markdown report (Data Health + Headline + four labeled sections). The Skill renders Notion blocks from THIS string, not from the structured fields above. The structured fields are preserved for Phase 2 block-type-per-section rendering and for `summary.json` capture. |

Validation order, first failure wins:

1. The argument is a dictionary.
2. Every required key is present.
3. `run_date` matches `^\d{4}-\d{2}-\d{2}$`.
4. `data_health` is a dict and contains `snapshot_dates` (dict) and `stale_tables` (list).
5. `working`, `not_working`, `patterns` are lists. `open_questions` is a list. `markdown_body` is a non-empty string.

Any failure at this stage returns `{ "ok": false, "error": <human-readable>, "category": "input_invalid" }`. No MCP call has been made yet, so there is no transport state to clean up.

## Resolving the target page

Read `NOTION_REPORT_PAGE_ID` from the environment. The variable name is exactly `NOTION_REPORT_PAGE_ID`, matching `.env.example` and `docs/runbook.md`. Do not look for any shorter alias. Both dashed (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) and undashed UUID forms are accepted by the MCP wrapper per the Wave-0 probe in `01-01-PROBE-NOTES.md`, so pass the raw env-var value through without normalization.

If the env var is unset or empty, return:

```json
{ "ok": false, "error": "NOTION_REPORT_PAGE_ID is not set", "category": "env_missing" }
```

Do NOT log the value itself in the error message, ever. The recovery step lives in `docs/runbook.md` § "Notion write failed".

Before the create call, run a preflight `mcp__claude_ai_Notion__notion-fetch` against the env-var value. A successful preflight is a response with `metadata.type == "page"` and no error key. If the preflight returns an error (404, permission_denied, transport), map it to a category per Section 7 and return the structured failure without attempting the create call. The preflight is cheap (1 read), catches the most common operator-side misconfiguration before any page is written, and matches the Skill-owned preflight pattern documented in the probe notes.

## Writing the page

Once preflight passes, call `mcp__claude_ai_Notion__notion-create-pages` to create a new child page under the parent. Per the Wave-0 probe in `01-01-PROBE-NOTES.md`, the MCP wrapper around `notion-create-pages` mirrors the Notion REST `POST /v1/pages` shape, with the parent specified as a `page_id` (both dashed and undashed UUID forms accepted), `properties.title` carrying the page title, and `children` carrying the rendered block array.

Invocation arguments:

```json
{
  "parent": {
    "type": "page_id",
    "page_id": "<value of NOTION_REPORT_PAGE_ID, passed through unchanged>"
  },
  "properties": {
    "title": {
      "title": [
        {
          "type": "text",
          "text": { "content": "Weekly report, <run_date>" }
        }
      ]
    }
  },
  "children": [ /* rendered Notion blocks per Section 6 */ ]
}
```

Title rule: format the title as `Weekly report, {run_date}` (comma separator, never a dash, per the voice rule in `CLAUDE.md`). Use the input dict's `run_date` verbatim. The title is the only `properties` field accepted when the parent is a page (Notion REST constraint).

100-block cap: the Notion API rejects a single `create-pages` call where `len(children) > 100`. The Phase 1 report renders to fewer than 50 blocks, so a single call is sufficient today. The Skill MUST still defensively check `len(children) <= 100` before invoking, and, if exceeded, send the first 100 blocks in the create call and append the remainder via the block-children-append MCP equivalent in batches of `<= 100`. If neither the wrapper nor a sibling append tool is available in the session, return `{ "ok": false, "error": "rendered block count <N> exceeds 100 and no append-children tool is available", "category": "transport_error" }` rather than silently truncating.

## Rendering the report

Render `markdown_body` to Notion blocks using a small, deterministic per-line classifier. Walk the body once, top to bottom, splitting on blank lines into logical blocks; classify each logical block by its leading characters; emit the matching Notion block type. For the stale-table flags inside the Data Health section, override the default paragraph classification with a `callout` block.

Per-section block mapping (Phase 1):

| Report section | Notion blocks emitted (in order) |
|---|---|
| Title (page title) | Set via `properties.title`, not emitted as a child block |
| Data Health | `heading_2("Data Health")`, then one `paragraph` (or `table`-shaped paragraph) for the per-table snapshot summary, then one `callout` per entry in `data_health.stale_tables` with `icon.emoji = "⚠️"` and `color = "yellow_background"` |
| Headline | `divider`, `heading_2("Headline")`, `paragraph(headline text)` |
| What is working | `divider`, `heading_2("What is working")`, one or more blocks rendered from whatever `markdown_body` contains for the section. The recipe (Step 6 § 3) supplies real findings or one of two explicit empty-state lines: `Nothing material to report this week.` or the D-12 stale-table disclaimer (e.g., `Watch-time and traffic-source analysis is unavailable: daily_video_analytics is 89 days stale (see Data Health).`). The Skill renders the literal `markdown_body` text without inspecting the line; do not enforce a specific placeholder string here. NEVER omit the heading. |
| What is not working | `divider`, `heading_2("What is not working")`, blocks from `markdown_body` (same empty-state rules as above) |
| Patterns worth watching | `divider`, `heading_2("Patterns worth watching")`, blocks from `markdown_body` (same empty-state rules as above) |
| Open questions | `divider`, `heading_2("Open questions")`, one `bulleted_list_item` per entry in `open_questions`, or a single `paragraph` saying "None recorded this run." if the list is empty |

Per-line classifier (applied to each logical block from `markdown_body`):

1. `# <text>` → `heading_1`
2. `## <text>` → `heading_2`
3. `### <text>` → `heading_3`
4. `- <text>` or `* <text>` → `bulleted_list_item`
5. `1. <text>` (any digit prefix) → `numbered_list_item`
6. `---` alone on a line → `divider`
7. Line matches the stale-table flag pattern (regex: a table name from `data_health.snapshot_dates` keys, followed by `: <N> days stale`, OR contains the `⚠` character) AND we are inside the Data Health section → `callout` with `icon.emoji = "⚠️"` and `color = "yellow_background"`
8. Default → `paragraph`

Empty sections MUST be emitted with their `heading_2` plus whatever the recipe placed in `markdown_body` for that section (an explicit `Nothing material to report this week.` paragraph or a D-12 stale-table disclaimer). NEVER silently omit a section heading. The Skill does not interpret the body string; the recipe's Step 6 owns the empty-state wording.

Paragraph chunking: Notion's `text.content` field caps at 2,000 characters. To stay safely under that cap, split any logical block whose rich-text content exceeds 1,900 characters into multiple blocks of the same type. Phase 1 paragraphs are well under 500 characters, so this guard is defensive but mandatory.

Block construction reference (verified against [developers.notion.com/reference/block](https://developers.notion.com/reference/block)):

```json
// heading_2
{ "object": "block", "type": "heading_2", "heading_2": { "rich_text": [
  { "type": "text", "text": { "content": "Data Health" } }
] } }

// paragraph
{ "object": "block", "type": "paragraph", "paragraph": { "rich_text": [
  { "type": "text", "text": { "content": "..." } }
] } }

// callout (stale-data flag)
{ "object": "block", "type": "callout", "callout": {
  "rich_text": [{ "type": "text", "text": { "content": "daily_video_analytics: 89 days stale" } }],
  "icon": { "type": "emoji", "emoji": "⚠️" },
  "color": "yellow_background"
} }

// divider
{ "object": "block", "type": "divider", "divider": {} }

// bulleted_list_item
{ "object": "block", "type": "bulleted_list_item", "bulleted_list_item": { "rich_text": [
  { "type": "text", "text": { "content": "..." } }
] } }
```

All text content is rendered as `rich_text[].text.content` (literal text), never as raw Markdown. Notion does NOT evaluate Markdown directives in `text.content`, which doubles as a prompt-injection guard for arbitrary row content sourced from BigQuery.

## Return shape and error handling

The Skill MUST always return a structured dictionary. It MUST NEVER raise. The analyzer (the `/run-analyzer` recipe in Plan 03) needs to write `summary.json` even when the Notion write fails, and a raised exception inside the Skill breaks that contract.

Success shape:

```json
{ "ok": true, "page_id": "<uuid from create response>", "url": "<url from create response>" }
```

Failure shape:

```json
{ "ok": false, "error": "<human-readable message, never the env-var value>", "category": "<one of the six below>" }
```

Canonical error categories (the runbook's section headings map one-to-one to these strings, so an operator looking at `summary.json.errors[].category` can find the right recovery section):

| Category | When to emit |
|---|---|
| `input_invalid` | The input dict failed validation (missing key, wrong type, malformed `run_date`, empty `markdown_body`). No MCP call was made. |
| `env_missing` | `NOTION_REPORT_PAGE_ID` is unset or empty. No MCP call was made. |
| `parent_not_found` | The preflight `notion-fetch` returned 404 `object_not_found`, OR the create call returned 400 `validation_error` referencing `parent.page_id`. The parent UUID is wrong, malformed, or the page was deleted. |
| `permission_denied` | The preflight or create call returned 404 because the Notion integration cannot see the page. (Notion intentionally returns 404 rather than 403 for missing-access cases, to avoid leaking page existence.) Recovery: re-add the integration to the parent page in Notion. |
| `transport_error` | 429 rate-limit, MCP tool not loaded in this session, network-level failure, or rendered block count exceeded 100 with no append-children tool available. |
| `unknown` | Any error not matching the above. The error string should include the underlying exception or response text so the runbook reader can extend the catalog. |

Error-category mapping table (paste-derived from `01-RESEARCH.md` §2, Error modes):

| Underlying failure | Detection | Skill `category` |
|---|---|---|
| `NOTION_REPORT_PAGE_ID` unset/empty | env-var resolution step | `env_missing` |
| Parent UUID malformed | API 400 `validation_error` mentioning `parent.page_id` | `parent_not_found` |
| Parent UUID valid but page deleted | API 404 `object_not_found` | `parent_not_found` |
| Integration not added to page | API 404 (Notion masks no-access as 404 on purpose) | `permission_denied` |
| Rate limited | API 429 with `Retry-After` header | `transport_error` |
| MCP tool not loaded in session | Tool-not-found error from Claude Code | `transport_error` |
| `children` array > 100 with no append-children tool | Pre-call check inside the Skill | `transport_error` |
| Input dict missing required key | Validation step before any MCP call | `input_invalid` |
| Anything else | Unmatched exception or response | `unknown` |

Per `CLAUDE.md` § "Tooling notes", the analyzer never calls Notion directly. This Skill is the only Notion writer in the project. If you are reading this file because you are the analyzer mid-run, hand the assembled report dict to this Skill and consume the return value; do not reach for `notion-create-pages` yourself.
