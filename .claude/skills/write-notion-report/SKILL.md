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
