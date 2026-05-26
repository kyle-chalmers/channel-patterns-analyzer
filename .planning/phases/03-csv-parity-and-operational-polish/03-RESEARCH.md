# Phase 3: CSV Parity and Operational Polish - Research

**Researched:** 2026-05-26
**Domain:** CSV-mode parity, cloud /schedule routine launch, runbook expansion
**Confidence:** HIGH (Phases 1+2 are shipped and verifiable on disk; cloud routine docs fetched live)

## Summary

Phase 3's CONTEXT.md was written 2026-05-25 while Phase 1 was mid-research and Phase 2 had not started. Both phases have now shipped (commits land through `a1d6483`, 2026-05-26). The Phase 3 locked decisions D-01 through D-04 still hold, but two of their grounding assumptions need to be qualified before planning, and one needs a hard correction:

1. **D-02 is broken as written.** `.claude/commands/run-analyzer.md` references `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md` and `02-RESEARCH.md` in six places (recipe lines 67, 133, 144, 213, 215, and the `02-CONTEXT.md` re-mention on 213). Those files exist in the repo but the references read as `D-08 from .planning/phases/02-honest-analyst-depth/02-CONTEXT.md` — a cloud routine pasting the recipe verbatim and cloning the repo would still resolve them (because cloud sessions clone the repo, and `.planning/` is committed). However a cloud routine that did NOT clone this repo would not, and the references are noise inside a routine system prompt either way. Phase 3 must either (a) dereference these into the recipe inline, or (b) verify the cloud routine always clones the repo and the references are tolerable as comments.
2. **D-01 is correct AND load-bearing in a way the CONTEXT didn't flag.** Cloud routines run on Anthropic's cloud environment, and Anthropic's published installed-tools table (https://code.claude.com/docs/en/claude-code-on-the-web) does NOT include `bq` or `gcloud`. The cloud routine cannot use the `bq_cli` transport branch even if it wanted to. The BigQuery MCP connector is the only path. The recipe's Step 1 transport probe already handles this, but `docs/schedule.md` must say so explicitly.
3. The Phase 1+2 build surfaced six runbook-worthy failure modes that CONTEXT.md did not enumerate. They are documented in §5 below.

**Primary recommendation:** Lock the stdlib CSV-engine default (CONTEXT.md D-CSV-default), dereference six `.planning/` references in the recipe into self-contained recipe text, and write schedule.md against the concrete cloud-routine field names from the live claude.com docs.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CSV-mode read of fixtures | Local Python stdlib | — | Recipe owns it via `scripts/csv_query.py` helper; cloud routine does not run CSV mode (D-01 anchors cloud on BigQuery MCP) |
| BigQuery query dispatch (local) | `bq` CLI | BigQuery MCP fallback | Phase 1 D-03 transport probe already wired |
| BigQuery query dispatch (cloud) | BigQuery MCP | — | `bq` CLI not available in cloud environment (verified against installed-tools table 2026-05-26) |
| Notion write | `write-notion-report` Skill | — | Phase 1 NOTION-03 contract; works identically in local + cloud per recipe |
| /schedule routine config | Anthropic claude.com UI | — | FLOW-01 (versioning in repo) deferred to v2; Phase 3 documents the UI walkthrough only |
| Failure-mode recovery docs | `docs/runbook.md` | `CHANGELOG.md` (audit trail) | ERR-01 / ERR-03; manual discipline, no automation |
| Fixture regeneration | `scripts/csv_fallback_loader.py` | — | CSV-mode-only; recipe invokes the loader when `DATA_SOURCE=csv` |

## Phase 1 + 2 Ground-Truth Check

### What Phase 1 actually shipped

`.claude/commands/run-analyzer.md` is a single 348-line markdown file (the recipe is one document, no parallel CSV variant), with the following structural shape:

| Step | Implements | Output |
|------|-----------|--------|
| 0. Preflight | env-var check, `run_date`, mkdir | minimal `summary.json` with `env_missing` if a var is unset; STOPs |
| 1. Probe transports | `bq` CLI → BigQuery MCP → STOP | sets `$TRANSPORT` |
| 2. Data health | `sql/04_data_health_check.sql` via `$TRANSPORT` | `runs/{date}/queries/data_health.json`, `stale_tables` list, `SIMULATE_STALE` override seam |
| 3. Top videos pull | `sql/02_top_full_length_videos.sql` | `runs/{date}/queries/top_full_length_videos.json` |
| 4. Prior reports (Phase 2) | reads up to 3 `reports/*.md` + sibling `summary.json` | working memory + `prior_reports_consulted` |
| 5. Eligible count (Phase 2) | inline eligible-count SQL via `$TRANSPORT` | `runs/{date}/queries/eligible_video_count.json` |
| 6. Draft report (Phase 2) | applies 6 CLAUDE.md sections, six-section structure with D-11/D-12 | `reports/{date}.md` + `runs/{date}/report.md` |
| 7. Self-audit (Phase 2) | 17-item copy-into-response checklist (D-01 Layer 2) | working-memory `voice_audit.checks_passed` / `fixes_applied` |
| 8. Assemble report dict | 8-key dict matching Skill input contract | working memory |
| 9. Invoke `write-notion-report` Skill | MCP create-pages via Skill | Notion child page or structured failure |
| 10. Write `summary.json` LAST | full 20+-field schema | `runs/{date}/summary.json` |
| 11. Operator message | SUCCESS / NOTION-FAIL / BQ-FAIL exhaustive triple | stdout |

The Skill (`.claude/skills/write-notion-report/SKILL.md`) is committed in the repo (the `.gitignore` has a specific negation for it — verified). It renders Notion blocks from `markdown_body` (not from the structured per-section fields, which are reserved for future enrichment). Validated end-to-end against live Notion 2026-05-25: `summary.json:22-24` shows `notion_write_ok: true`, `notion_url: https://www.notion.so/36bccd0549458159a49dd99439757982`.

The published 2026-05-25 report at `reports/2026-05-25.md` carries all six sections in order with explicit placeholder bodies in the four sections Phase 1 left empty ("Not analyzed this run. ...").

### What Phase 2 added that the CSV path must mirror

Phase 2's contribution is mostly in the recipe's draft and pre-draft steps. The CSV path must produce the same artifacts:

| Phase 2 artifact | CSV path must produce | Note |
|------------------|------------------------|------|
| `runs/{date}/queries/eligible_video_count.json` (Step 5 inline SQL result) | yes | CSV engine must support this query shape, including `LEAST()` across two subqueries and `DATE_DIFF` with Phoenix tz |
| `summary.json.prior_reports_consulted` | yes — same step 4 logic reads from `reports/` regardless of data source | No CSV-specific change |
| `summary.json.voice_audit` block | yes — same step 7 self-audit runs regardless of source | No CSV-specific change |
| `summary.json.warnings[]` (e.g., `simulate_stale_applied`) | yes — `SIMULATE_STALE` works with CSV-derived data_health rows | The override mutates in-memory rows; engine-agnostic |
| six-section report structure with D-11 empty bodies and D-12 stale-table disclaimers | yes — same draft step | The CSV fixtures need to support stale-table simulation if Phase 3 wants to exercise D-12 |

The eligible-count SQL (recipe lines 94-111) is the most complex query the CSV engine must support. It does: a `LEAST()` of two `MAX(snapshot_date)` subqueries, an `m.snapshot_date = (SELECT snapshot_date FROM latest_common)` filter, an `m.video_type = 'full_length'` filter, and a `DATE_DIFF(CURRENT_DATE("America/Phoenix"), DATE(m.published_at), DAY) >= 14` filter. This pushes the stdlib helper toward needing real date arithmetic, not just CSV row-filtering.

### CONTEXT.md assumptions that need qualifying

| CONTEXT.md assumption | Reality | Implication |
|----------------------|---------|-------------|
| "D-02: file must stay self-contained enough that copy-paste-into-routine is realistic (no project-local `@`-imports the cloud context cannot resolve)" | Recipe has no `@`-imports, but has six prose references to `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md` and `02-RESEARCH.md` (see §2 below). | Phase 3 must dereference or accept-with-caveat. |
| "Phase 1's Skill renders Notion blocks from `markdown_body` only" | Verified — SKILL.md:22, 26 confirm. CSV path produces the same `markdown_body`, so the Skill is data-source-agnostic. | No CSV-specific Skill work. |
| "existing 5 runbook sections cover bq-auth-local, stale table, missing/empty table, schema drift, and Notion write fail" | runbook.md has 6 named sections currently (the env-missing section was added in Plan 01-04). | CONTEXT.md was written before Plan 01-04 merged. Update the inventory: 6 existing, not 5. |
| "Phase 2's CONTEXT.md does not exist yet" | It exists (`.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`), as do RESEARCH.md, VERIFICATION.md, REVIEW.md, and three PLAN+SUMMARY pairs. | Phase 3 planner can read them; reading them is no longer aspirational. |
| Cloud routine smoke-test will rely on "BigQuery web connector authorized" | The Phase 2 VERIFICATION.md frontmatter notes the SIMULATE_STALE path is unexercised; the Phase 3 smoke test could also exercise that as a side benefit (catch two birds). | D-03 checklist can usefully include `SIMULATE_STALE` as a 5th verification, OR Phase 3 explicitly tracks SIMULATE_STALE testing separately as a non-D-03 item. |

## `run-analyzer.md` Cloud-Portability Audit

D-02 says the recipe must be paste-into-routine-able. Auditing the 348-line file:

### `.planning/` references (6 total, all in recipe prose, all in Step 4 / Step 6 / Step 7)

| Recipe line | Reference text | Severity | Recommended action |
|------------|---------------|----------|-------------------|
| 67 | "This step implements ANALYSIS-05 and D-08 from `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`" | Low — D-08's rule is restated inline lines 76-81. Reference is justificatory, not load-bearing for execution. | Dereference: replace with "(per Phase 2 D-08, which is summarized below)" or remove entirely. |
| 133 | "implements REPORT-01 (six-section structure), REPORT-02 ..., and the D-07 inline-parenthetical format (per `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`)" | Low — D-07's format is restated lines 148-162. | Dereference or remove the parenthetical. |
| 144 | "Apply D-08 from `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`" | Medium — restated inline immediately after, but the literal reference reads as a doc pointer. | Dereference. The rule is "Do not cite prior reports in prose. Banned phrases: ..." — that text suffices. |
| 213 | "This step implements D-01 Layer 2 from `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`" | Low — sentence continues with the full rule inline. | Dereference. |
| 215 | "(cited in `.planning/phases/02-honest-analyst-depth/02-RESEARCH.md` § 'Common Pitfalls' 3)" | Low — pattern (copy-into-response checklist) is implemented in full below. | Remove the parenthetical entirely. |
| 215 (same line) | "The checklist mirrors `CLAUDE.md` and `02-CONTEXT.md` rules 1:1" | Medium — `02-CONTEXT.md` here is ambiguous (no path), could read as a reference. | Replace with "CLAUDE.md rules and the Phase 2 decision record". |

**Verdict:** None of the references are load-bearing for execution — every D-NN rule cited has its text restated inline. But "self-contained enough for copy-paste-into-routine" (D-02's exact language) is violated in spirit: a cloud routine reading the system prompt is being pointed at files outside the prompt. Phase 3 should dereference all six.

### Other files referenced in recipe

| Reference | Available in cloud? | Note |
|-----------|--------------------|------|
| `CLAUDE.md` (5+ section references by title) | YES — cloned with repo | Loads via repo clone at routine session start |
| `BUSINESS_RULES.md` | YES — cloned with repo | Same |
| `sql/02_top_full_length_videos.sql`, `sql/03_age_controlled_performance.sql`, `sql/04_data_health_check.sql` | YES — committed | Recipe reads them at runtime |
| `runs/README.md` (schema doc) | YES — committed | Referenced for `voice_audit` shape |
| `reports/*.md` archive | YES — committed (`reports/` is NOT gitignored — verified `.gitignore` lines 1-50) | Step 4 prior-report read depends on these being in the repo |
| `scripts/csv_fallback_loader.py` | YES — committed | Phase 3 will add a `--snapshot-date` arg |
| `.env` file | NO — gitignored | Cloud routine reads env vars from per-routine UI config instead |
| `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly` | YES if connector authorized | This is the cloud's BigQuery path |
| `mcp__claude_ai_Notion__notion-*` tools | YES if connector authorized | This is the cloud's Notion path |

### Assumed tools the cloud routine will or will not have

| Tool | Cloud availability | Source |
|------|-------------------|--------|
| `bq` CLI | **NO** — not in installed-tools table | code.claude.com/docs/en/claude-code-on-the-web installed-tools section, verified 2026-05-26 |
| `gcloud` CLI | NO | Same source |
| Python 3.x + stdlib | YES | Same — "Python 3.x with pip, poetry, uv, black, mypy, pytest, ruff" |
| `bash`, `grep`, `ls`, `sort`, `printf` | YES | Standard Ubuntu 24.04 base image |
| `jq`, `yq`, `ripgrep` | YES | Same source ("Utilities") |
| `git` | YES | Same |
| BigQuery MCP connector | YES if authorized in user's Anthropic account | Kyle confirmed 2026-05-25 |
| Notion MCP connector | YES if authorized | Phase 1 used this end-to-end |

**Conclusion:** D-02 is mostly safe but has the six prose references to fix. The bigger consequence is that the cloud routine's `$TRANSPORT` is **forced** to `bq_mcp` (not a probe outcome). Phase 3 should consider whether the recipe should detect cloud-vs-local and skip the probe, OR whether the probe's existing fallback to `bq_mcp` is fine because the probe will just fail the `bq` check and fall through. Both work; the probe-fallback path is simpler.

## CSV Engine Recommendation (stdlib vs DuckDB)

CONTEXT.md defaulted to "stdlib helper returning JSON shaped like `bq query --format=json`" with the alternative being "DuckDB-reads-CSV-directly." Researcher's brief was to weigh both. Tradeoffs against the actual code Phases 1+2 shipped:

### Stdlib `scripts/csv_query.py`

| Pro | Con |
|-----|-----|
| Zero new dependencies — preserves PROJECT.md "no new Python packages without justification" | Must hand-implement four query shapes: data_health (`MAX(snapshot_date)` per table + `days_stale`), top videos (cross-table join on `(video_id, snapshot_date)` + age filter), eligible_count (`LEAST()` of two `MAX(snapshot_date)`, age filter), and any future query |
| Output shape is whatever we want it to be — can match `bq query --format=json` exactly | Date arithmetic (`DATE_DIFF` with Phoenix tz) must be reimplemented in Python; getting timezone semantics identical to BigQuery is fiddly |
| Easy to commit and review (one file, ~150 lines) | A 5th SQL file (Phase 3 + 1 follow-up) would mean adding a 5th handler function — drift risk between SQL and Python |
| Recipe-engine handoff is clean: recipe says "if `DATA_SOURCE=csv`, invoke `python scripts/csv_query.py <query_name>` instead of `bq query`" | Output JSON shape parity requires careful matching of column names, integer-vs-string coercion (BigQuery returns numerics as JSON strings; csv module returns as strings naturally — happy accident, but worth noting) |

### DuckDB reads CSVs directly

| Pro | Con |
|-----|-----|
| **Re-runs the exact same `sql/*.sql` files against CSVs** with no Python query handlers. `DuckDB` has `read_csv_auto()` and aliases that make a CSV look like a table. | New Python package required — `duckdb` is ~30MB wheel. PROJECT.md Constraints say "no new packages without justification." Justification exists (single SQL source of truth), but it's a real install. |
| Same SQL = no drift risk between SQL and CSV. Phase 4 adds `sql/05_*.sql`, CSV-mode picks it up automatically. | DuckDB SQL dialect differs from BigQuery in small ways. `CURRENT_DATE("America/Phoenix")` — DuckDB supports tz-aware `now()` but `CURRENT_DATE` with a string argument is not standard. The `DATE_DIFF` signature differs (`date_diff('day', a, b)` in DuckDB vs `DATE_DIFF(a, b, DAY)` in BigQuery). Backticks-vs-no-backticks for table names. Either we maintain two SQL dialects, or we abstract them, or we hit subtle bugs. |
| The eligible-count SQL (inline in the recipe) would work unchanged. | DuckDB's CSV reader respects header types only if asked. The CSVs from `csv_fallback_loader.py` write numbers without quoting, so types should infer correctly, but this is one more thing to verify. |
| DuckDB is well-known to viewers — the channel covers data engineering tools. Using it is on-brand. | DuckDB CLI is NOT in the cloud environment's installed tools either; would need a `pip install duckdb` step. CSV mode is local-only by design (D-01 anchors cloud on BigQuery MCP), so this isn't blocking — but it does mean DuckDB joins the dependency surface area only for local CSV runs. |

### Recommendation

**Lock the stdlib default.** Three load-bearing reasons:

1. **BigQuery SQL syntax does NOT round-trip to DuckDB without translation.** The shipped `sql/02`, `sql/03`, `sql/04` all use `CURRENT_DATE("America/Phoenix")` (BigQuery's tz-aware form). DuckDB's equivalent is `current_date AT TIME ZONE 'America/Phoenix'` or a `now() AT TIME ZONE ...` expression. The `DATE_DIFF` order is reversed. The backtick-quoted `\`youtube_analytics.table\`` form is BigQuery-specific. To make the same SQL files run in both, we'd need a dialect-translation layer, which is more code than four hand-written Python query handlers.

2. **The query surface is small and stable.** Three canonical `sql/` files + one inline eligible-count query = four query shapes. Phase 3 adds zero new SQL files. v2 (RICH-*, TREND-*) is the next time the query count grows, and by then the channel may be on a different stack anyway. The drift risk is bounded.

3. **PROJECT.md Constraints are an explicit project value.** "Stack reads as 'shell + SQL + Claude' viewers can replicate without learning a Python SDK." Adding DuckDB is a viewer-facing signal that the analyzer needs a real query engine. Stdlib keeps the demo simple.

**Counter-recommendation (if Kyle disagrees with the lock):** If DuckDB feels significantly cleaner once the planner sees the stdlib query-handler code, the escape hatch is `sql/*.duckdb.sql` sidecar files — one per `sql/*.sql`, hand-translated, committed alongside. Adds a maintenance burden but keeps the SQL-source-of-truth principle. Recommend against unless the stdlib path proves uglier than expected.

## CSV Output JSON Shape Contract

The downstream draft step (Step 6) expects the data captured in `runs/{run_date}/queries/*.json` to have the same shape regardless of source. Concrete examples from the live 2026-05-25 run:

### `data_health.json` shape

From `runs/2026-05-25/queries/data_health.json` (live BigQuery `bq query --format=json`):

```json
[
  {"days_stale":"0","latest_snapshot":"2026-05-25","table_name":"daily_video_stats"},
  {"days_stale":"0","latest_snapshot":"2026-05-25","table_name":"video_metadata"},
  {"days_stale":"0","latest_snapshot":"2026-05-25","table_name":"daily_video_analytics"},
  {"days_stale":"0","latest_snapshot":"2026-05-25","table_name":"daily_traffic_sources"}
]
```

Key observations the CSV engine must match:

- **Top-level is a JSON array** (not an object with a `rows` key, despite the BigQuery MCP returning the latter wire shape — recipe Step 1 handles that conversion).
- **All values are JSON strings.** `days_stale` is `"0"`, not `0`. BigQuery's `bq query --format=json` coerces numerics to strings by default. The CSV stdlib helper should emit strings for parity (downstream parses them as needed).
- **Column names match the SQL `SELECT` column aliases verbatim.** Order is not guaranteed in JSON objects but the recipe walks each row by key name, not index.

### `top_full_length_videos.json` shape

From the same run (truncated):

```json
[{"comment_count":"7","days_since_published":"199","duration_formatted":"26:50","like_count":"111","published_at":"2025-11-07 13:01:07","title":"Claude Code vs Manual Jira Ticket Work | The Difference Is Amazing","video_type":"full_length","view_count":"10271"}, ...]
```

Same conventions: array of objects, all string values, column names match the SQL.

### `eligible_video_count.json` shape (Phase 2, not yet exercised live)

Per the recipe lines 94-111, the SQL `SELECT` produces three named columns: `eligible_count`, `total_full_length`, `latest_common_snapshot`. CSV engine must emit a one-row JSON array with those three keys, all string values.

### CSV path contract

`scripts/csv_query.py` (or whatever the planner names it) MUST:

1. Accept a query identifier (e.g., `data_health`, `top_full_length_videos`, `eligible_video_count`).
2. Read the appropriate `sample_data/*.csv` file(s).
3. Apply the same filters/joins/aggregations the corresponding SQL file applies, computed in Python.
4. Emit JSON to stdout in the format above (array of objects, all string values).
5. Honor `BQ_DATASET` — the helper should accept the env var for forward-compat even though CSV mode doesn't actually have a dataset (helps keep recipe Step 1 symmetric).

The recipe Step 1 invocation should become a three-branch probe:

- If `DATA_SOURCE=csv`, set `TRANSPORT=csv` and the subsequent `Dispatch ... to $TRANSPORT` steps invoke the CSV helper instead of `bq`/MCP.
- Else if `command -v bq`, set `TRANSPORT=bq_cli`.
- Else if BigQuery MCP loaded, set `TRANSPORT=bq_mcp`.
- Else write `no_bigquery_transport` error and STOP.

The "if CSV, regenerate fixtures first" step (CONTEXT.md CSV freshness default) sits BEFORE Step 1's probe: when `DATA_SOURCE=csv`, the preflight runs `python scripts/csv_fallback_loader.py` with today's Phoenix date, then proceeds normally.

## Failure Mode Inventory from Phase 1 + 2 Commits

Walking commits `4baf347`..`a1d6483` plus `runs/2026-05-25/summary.json.warnings` and `01-04-SUMMARY.md` § "Recipe defects surfaced":

### Failure modes hit during build (need runbook entries)

| # | Failure mode | Source | Already in runbook? | Disposition |
|---|-------------|--------|--------------------|-----|
| 1 | `bq query --max_rows=10000` crashes bq with Python `RecursionError` | Phase 1 live run 2026-05-25; `01-04-SUMMARY.md` line 149 | NO — was a recipe bug, fixed in Plan 02-02 (commit `769f4a8`) | Add a "Why the recipe pipes SQL via stdin" footnote in runbook AND/OR add a section "Recipe edits that crash bq" for future-proofing |
| 2 | Positional SQL with Unicode box-drawing chars (`─` U+2500) crashes bq's flag parser | Phase 1 live run; `01-04-SUMMARY.md` line 150 | NO — same as #1, recipe fix landed in Plan 02-02 | Same disposition as #1 |
| 3 | Phase 1's `--max_rows=10000` flag silently accepted as a global head-style flag but ignored for `query` | `summary.json:26` warnings | NO | Noted; rolled into #1 footnote |
| 4 | Operator runs same recipe twice on the same day; both runs would clobber `reports/{date}.md` | Implicit in `docs/maintenance.md` "Re-running after a failure" — uses `-2` suffix | YES (docs/maintenance.md, not runbook) | Already documented; ensure the cloud-routine smoke test in D-03 doesn't accidentally trigger this |
| 5 | `SIMULATE_STALE` exists as a seam but no live test has exercised it | Phase 2 VERIFICATION.md `human_verification` item 2 | NO | Phase 3 smoke test can exercise this; add a runbook note "How to test the stale-data path without waiting for real stale data" |
| 6 | `(label, n=N)` parentheticals through `write-notion-report` Skill unconfirmed | Phase 2 VERIFICATION.md `human_verification` item 3 | NO | Phase 3 smoke test on real data will resolve; if rendering mangles, runbook gets a new section |

### Cloud-specific failure modes (CONTEXT.md called these out — need new sections)

| # | Cloud failure mode | Trigger |
|---|--------------------|---------|
| 7 | BigQuery MCP connector not authorized in user's Anthropic account | First `/schedule` run after creation; routine session has no `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly` tool |
| 8 | Notion MCP connector not authorized | Same shape; Skill fails with `category: env_missing` or `transport_error` |
| 9 | Routine env var missing (`NOTION_REPORT_PAGE_ID`, `BQ_PROJECT`, `BQ_DATASET`) | Routine config in claude.com UI doesn't include the var → recipe Step 0 stops with `env_missing` |
| 10 | Routine run timed out (long BigQuery query, network slowness, hung MCP) | Anthropic UI shows the session as not-completed; no `summary.json` if the recipe didn't reach Step 10 |
| 11 | Anthropic UI shows error before recipe even runs (cloud environment broken, repo clone failed, network policy blocks an outbound) | No `summary.json` at all; debugging is in the routine session transcript |
| 12 | Network policy on the cloud environment blocks an outbound call the routine needs | `Trusted` default allowlist may not include `*.notion.so` or BigQuery API endpoints directly (MCP traffic routes through Anthropic, so this is unlikely to bite, but documented) |

**Runbook total after Phase 3:** 6 existing + (1 or 2 from inventory items 1-3 collapsed into one) + (1 from #5) + 5 cloud (items 7-11) = **12-13 named sections.**

### Items the planner should explicitly NOT add

- `skill_unavailable`, `report_dict_invalid`, `no_bigquery_transport`. Phase 1's `01-04-SUMMARY.md` line 54 deferred these to Phase 3 (ERR-01). The recipe Step 9 and Step 1 produce structured errors with these category names; runbook needs a section per category so operator messages have a target.
- A "recipe was paste-edited mid-routine and now diverges from repo" section. CONTEXT.md D-02 explicitly accepts the risk via "editing the recipe means re-pasting into the routine (a CHANGELOG-worthy event)." No runbook section needed; the CHANGELOG discipline IS the documentation.

## Cloud Routine Setup Walkthrough Requirements

Verified live against https://code.claude.com/docs/en/routines, 2026-05-26. D-04 says the walkthrough needs concrete field names. Here they are:

### Routine creation form fields (in display order)

1. **Routine name** — free-text input. Recommended value: `channel-patterns-analyzer-weekly` (matches CONTEXT.md "Specific Ideas" recommendation).
2. **Prompt** (the system prompt input box) — multiline text. Includes a model selector. **Paste-target for `.claude/commands/run-analyzer.md`.** Model: recommend Sonnet 4.5 or Opus 4.x depending on what's current; the recipe doesn't depend on any model-specific feature, but draft quality benefits from larger context.
3. **Repositories** — multi-select GitHub repo picker. Recommended: select `channel-patterns-analyzer`. Recipe Step 4 prior-report read depends on the repo being cloned, so this is non-optional.
4. **Environment** — dropdown. Use the **Default** environment (network access `Trusted`, no custom setup script needed for BigQuery MCP path).
5. **Select a trigger** — pick **Schedule**, then a preset:
   - Frequency: **Weekly**
   - Day: **Monday**
   - Time: **9:00 AM**
   - Timezone selector: **America/Phoenix** (the form's note says "Times are entered in your local zone and converted automatically" — if Kyle's machine is already on Phoenix time, just set 9am; otherwise pick the timezone explicitly).
6. **Connectors** section (at bottom of form, in a Connectors tab) — verify the **BigQuery (Google Cloud)** and **Notion** connectors are listed. Both should already be enabled in Kyle's account per CONTEXT.md D-01 ("Kyle confirmed BigQuery MCP authorized 2026-05-25"). Remove any other connectors that aren't needed (Slack, Linear, etc.).
7. **Permissions** section — default is fine. The recipe writes to local files inside the cloned repo (`reports/`, `runs/`) and pushes via Claude's normal `claude/`-prefixed branch flow.
8. **Environment variables** — NOT a top-level form field; live under the environment's settings. To set: open the environment's settings via the cloud icon below the Instructions box → settings icon → Environment variables. Add three:
   - `NOTION_REPORT_PAGE_ID=<from Kyle's .env>`
   - `BQ_PROJECT=primeval-node-478707-e9` (the value used in the 2026-05-25 live run)
   - `BQ_DATASET=youtube_analytics`

### Field-name verification notes

- The form's left panel is referred to as **Instructions** in the docs (the `Instructions` box) — this is what CONTEXT.md called the "system prompt."
- The button to start a manual run is **Run now** on the routine's detail page (after Create).
- The button at the bottom-right of the form is **Create** (not "Save").
- Past runs are listed on the routine's detail page; click a run to open it as a full session and read the transcript.
- Errors do NOT surface in a separate "logs" panel. The docs are explicit: "A green status in the run list means the session started and exited without an infrastructure error. It does not mean the task in your prompt succeeded. Open the run to read the transcript and confirm what Claude actually did. Blocked network requests, missing connector tools, and task-level failures all surface there rather than in the status indicator."

### Walkthrough rot risk

D-04 explicitly accepts that UI labels will rot. The Routines feature is in research preview (the docs page has a `<Note>` banner saying so), so field names may change. CHANGELOG.md entry per UI change is the discipline.

## Run-Now Checklist Scoping

D-03 specifies four verifications, "runnable in under 2 minutes." Walking each:

| # | Verification | Where to check | Realistic time |
|---|--------------|----------------|----------------|
| (a) | New child page appeared under `NOTION_REPORT_PAGE_ID` within 60s | Open the channel-patterns parent page in Notion; look for a new child titled `Weekly report, {today's Phoenix date}` | 30s |
| (b) | Page has all six required sections (Data Health, Headline, What is working, What is not working, Patterns worth watching, Open questions) | Same Notion page; scroll | 20s |
| (c) | `runs/{date}/summary.json` was written | The cloud-session repo writes to a `claude/`-prefixed branch by default. Check the routine session view in claude.com for the created PR or branch; open the file. Alternatively, after the PR merges, `git pull` locally and inspect. | 60s if the operator is set up to pull the branch; 90s if they have to navigate the session view |
| (d) | Anthropic UI shows the run as completed (not errored) | Routine detail page → past runs list → status indicator. **Caveat per the docs:** "green" means the session exited without infrastructure error, NOT that the task succeeded. The operator should also briefly open the run transcript and confirm no error keywords appear. | 30s |

**Total realistic time:** ~3 minutes if (c) requires PR navigation, ~2 minutes if the operator has the local repo cloned and can pull. CONTEXT.md's "under 2 minutes" is tight. Two options:

1. **Accept ~3 minutes** as the realistic ceiling. The "under 2 minutes" line is aspirational, not a contract.
2. **Compress (c) into (a):** the recipe writes the report markdown to `reports/{date}.md`. If we accept that the Notion page (verified in (a)) and `reports/{date}.md` are the same content (PERSIST-01 contract), then verifying the Notion content covers most of what verifying `summary.json` would have. We could move (c) to a "post-run sanity check after the PR merges" item that doesn't count against the 2-minute budget.

**Recommended:** Adopt option 2 — the four checklist items become:

- (a) child page exists with today's title
- (b) six sections present
- (c) Anthropic UI shows run completed without error
- (d) operator opens the run transcript and confirms no `category: ...` error lines

Then a separate "after the PR merges" note: pull the branch, verify `summary.json` has `notion_write_ok: true` and `errors: []` and (Phase 2) a non-empty `voice_audit.checks_passed` array. This is post-hoc verification, not part of the 2-minute Run Now budget.

### Additional gaps the planner should know

- **The 2026-05-25 live run is missing the Phase 2 `voice_audit` block** because that run was Phase 1. The first Phase 2 run will be the first time `voice_audit` lands in `summary.json`. Phase 3's smoke test will be the first cloud-routine run that exercises voice_audit at all. Expect this to surface latent issues (Phase 2 VERIFICATION.md item 3 documents the unverified `(label, n=N)` rendering path).
- **The smoke test should NOT include a SIMULATE_STALE pass** unless Kyle explicitly wants to roll the stale-disclaimer verification into Phase 3. Recommend: keep the Run Now checklist clean (4 items, happy path), and put SIMULATE_STALE as a separate "exercise the stale path once after launch" item in runbook.md.

## Tech Debt Scope Decision

From CONCERNS.md, items the planner should fold into Phase 3 vs defer:

| Item | Phase 3 scope? | Rationale |
|------|----------------|-----------|
| Timezone inconsistency in sql/02/03/04 (bare `CURRENT_DATE()` vs Phoenix tz) | **Already done** — Plan 02-01 (commit `45e6054`) fixed this | Verify in Phase 3 verification, no new work |
| `scripts/csv_fallback_loader.py:55,145` UTC mislabeling | **YES — Phase 3 scope** | Fix is part of CSV-01 work; CONTEXT.md CSV freshness default already says so |
| `--snapshot-date` arg to csv_fallback_loader | **YES — Phase 3 scope** | Same — CONTEXT.md CSV freshness default |
| `requirements.txt` cross-reference rot (`requirements-csv.txt`, `requirements-bigquery.txt` don't exist) | **YES — Phase 3 scope** | Naturally rides along with CSV-mode docs; one-line fix |
| Unused env vars in `.env.example` (`YOUTUBE_CHANNEL_ID`, `ANALYSIS_LOOKBACK_DAYS`, `MIN_VIDEO_AGE_DAYS`, `SCHEDULE_TIMEZONE`) | **YES — Phase 3 scope, REMOVE them** | CONTEXT.md `<canonical_refs>` explicitly says "Phase 3 cleans up unused env vars OR wires them through; planner picks." Recommend REMOVE: (a) `MIN_VIDEO_AGE_DAYS` is hardcoded in `sql/03` and CLAUDE.md; wiring requires a templating step the project doesn't have; (b) others have no current consumer; YAGNI. |
| BUSINESS_RULES.md section-number drift (runbook §5, §6, maintenance §6) | **Mostly already done** — Plan 01-04 fixed the runbook §5/§6 refs; verify `docs/maintenance.md:9` ("§6") is also fixed. Per CONCERNS.md it still references §6. | One-line fix; rides with the runbook work |
| `sql/01_latest_snapshot_overview.sql` checks only two tables | **DEFER** — Plan 02-01 commentary noted the scope; not in any Phase 3 requirement; the recipe doesn't run sql/01 | Add to CHANGELOG `Deferred` section if it isn't already |
| `LIMIT 20` ceiling in sql/02/03 | **Already removed** — Plan 02-01 commit `45e6054` | None |
| Hardcoded `youtube_analytics` dataset name in SQL files | **Already handled by recipe in-memory templating** (recipe Step 2 line 38 does the substitution) | No additional work |
| `sample_data/` is gitignored but present on disk | **YES — Phase 3 scope** | The CSV freshness default regenerates these every CSV-mode run, so leaving them gitignored is consistent. Add a note in the README that they're regenerated. |
| `requirements.txt` is all comments / no-op | Rides with the requirements.txt cross-ref fix above | Same |
| Public-facing repo notice missing from CLAUDE.md | **OPTIONAL** — not strictly Phase 3 scope, but cheap. Recommend YES if the planner has bandwidth | One-line addition per the user's global CLAUDE.md template |
| Test coverage gaps | **DEFER** — not Phase 3 scope; v2 territory | Already deferred in PROJECT.md / REQUIREMENTS.md |

## Validation Architecture

Per the Nyquist validation directive (config.json absent, default = enabled). The phase touches markdown docs, one Python script (`scripts/csv_fallback_loader.py`), a new Python helper (`scripts/csv_query.py` per recommendation), and a recipe-as-instructions file. There's no existing test framework in this repo.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (available in cloud env; not yet adopted in repo) |
| Config file | none — Wave 0 introduces if needed |
| Quick run command | `python -m pytest tests/ -x` (after Wave 0 creates `tests/`) |
| Full suite command | `python -m pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CSV-01 | `DATA_SOURCE=csv` produces a structurally identical report | smoke (live recipe run) | `DATA_SOURCE=csv` + manually run recipe; assert `reports/{date}.md` has all six section headings via `grep` | ❌ Wave 0 |
| CSV-01 | CSV-mode top-of-report carries the `data source: csv (sample fixtures, not live)` annotation | unit (string check on output) | `grep -F 'data source: csv' reports/{date}.md` | ❌ Wave 0 |
| CSV-02 | Every BigQuery query has a CSV equivalent | unit | `python scripts/csv_query.py <name>` returns a JSON array for each of: `data_health`, `top_full_length_videos`, `eligible_video_count` | ❌ Wave 0 |
| CSV-02 | CSV output JSON shape matches `bq query --format=json` | unit | `python scripts/csv_query.py data_health \| jq 'length, .[0] \| keys'` matches the live `runs/2026-05-25/queries/data_health.json` shape | ❌ Wave 0 |
| SCHED-01 | `docs/schedule.md` walks the operator through the cloud routine setup | manual-only (doc review) | Read top to bottom; verify the field names match the live UI | — |
| SCHED-01 | Schedule.md mentions both local and cloud variants | unit | `grep -E 'local\|cloud' docs/schedule.md \| wc -l` >= 4 | — |
| SCHED-02 | `write-notion-report` Skill works identically in both contexts | manual (smoke test from D-03 run-now checklist) | Run the routine via Run Now; verify Notion page renders correctly | — |
| ERR-01 | Every failure mode has a named runbook section | unit | `grep -c '^## ' docs/runbook.md` >= 12 (existing 6 + new 6 minimum) | — |
| ERR-01 | Each runbook section follows Symptom/Fix/Recording template | manual review | Read each new section; check for the three subheadings | — |
| ERR-03 | `CHANGELOG.md` has a Phase 3 entry naming new runbook sections | unit | `grep -c '## 2026-' CHANGELOG.md` increases by at least 1 | — |

### Sampling Rate
- **Per task commit:** `grep` checks on the modified file
- **Per wave merge:** the full unit-test commands above
- **Phase gate:** Run-now smoke test (D-03 checklist) + verify all runbook sections present

### Wave 0 Gaps
- [ ] `tests/test_csv_query.py` — covers CSV-02 shape contract
- [ ] `tests/conftest.py` — shared fixtures (snapshot fixtures pointing at `sample_data/`)
- [ ] OR: skip pytest entirely and rely on `grep`-based assertions documented in PLAN tasks (PROJECT.md "no application framework" arguably extends to test framework — recommend the planner pick the lighter path)

**Recommendation:** Skip pytest adoption in Phase 3. The CSV-engine work is small enough that grep-based `<verify>` blocks in the PLAN's task XML (per global CLAUDE.md planning standard) cover it. v2 work can adopt pytest if test surface grows.

## Open Questions for Planner

1. **Dereference the six `.planning/` references in the recipe, or accept them?**
   - What we know: They're prose annotations; every D-NN rule is restated inline immediately after.
   - What's unclear: D-02's "self-contained" language — strict reading says dereference; pragmatic reading says they're fine because the cloned repo provides them.
   - Recommendation: Dereference. Five-minute fix, removes ambiguity, no semantic loss.

2. **Should CSV mode regenerate fixtures unconditionally, or only when stale?**
   - What we know: CONTEXT.md CSV freshness default says regenerate every CSV-mode run (happy-path demo).
   - What's unclear: A `--snapshot-date` override is required, but should the loader skip the write when `sample_data/*.csv` are already today's date (with the override-aware check)?
   - Recommendation: Unconditional regeneration. Stable seeds (`Random(42)`, `Random(43)`, `Random(44)`) make the CSV content deterministic; rewriting is cheap; skipping adds branching logic for no real win.

3. **Should the recipe's transport probe explicitly handle CSV as the first branch, or as a parallel `DATA_SOURCE` check before the probe?**
   - What we know: Phase 1 D-03 establishes the probe pattern; CSV is the third branch CONTEXT.md envisions.
   - What's unclear: A `DATA_SOURCE=csv` env var should short-circuit the probe (don't probe `bq` at all if we know we're using CSV). Or treat it as another transport like the other two and let the probe walk all three?
   - Recommendation: Short-circuit. CSV is an explicit operator choice (`DATA_SOURCE=csv`), not a fallback. The probe should be `if DATA_SOURCE=csv → TRANSPORT=csv; else probe bq/MCP`.

4. **Should Phase 3 ship the `(label, n=N)` Notion rendering test as part of its smoke test?**
   - What we know: Phase 2 VERIFICATION.md flagged this as `human_needed` item 3.
   - What's unclear: Phase 3's smoke test will exercise it automatically (the recipe produces a Phase 2 report end-to-end). Worth calling out explicitly in the D-03 checklist?
   - Recommendation: Add as a sub-bullet under verification (b) — "in addition to confirming the six headings, spot-check one finding that should carry a `(label, n=N)` parenthetical, verify Notion renders it as plain text (not stripped, not linkified)."

5. **What's the right answer to "Cloud routine name"?**
   - What we know: CONTEXT.md "Specific Ideas" recommends `channel-patterns-analyzer-weekly`.
   - What's unclear: Anything.
   - Recommendation: Lock that name in schedule.md verbatim. No discretion needed here.

6. **The `.env.example` cleanup — remove the unused vars or wire them through?**
   - What we know: Four vars unused; PROJECT.md says simple is better; no current consumer.
   - What's unclear: `MIN_VIDEO_AGE_DAYS` and `SCHEDULE_TIMEZONE` might be "obvious" things users will look for and not finding them is also confusing.
   - Recommendation: Remove all four, add a comment block in `.env.example` explaining the analyzer's actual var list (`DATA_SOURCE`, `BQ_PROJECT`, `BQ_DATASET`, `NOTION_REPORT_PAGE_ID`). YAGNI.

## Environment Availability

| Dependency | Required By | Available (local) | Available (cloud routine) | Fallback |
|------------|------------|-------------------|---------------------------|----------|
| Python 3.x stdlib | CSV-01 helper, csv_fallback_loader | YES | YES (per installed-tools table) | — |
| `bq` CLI | Recipe Step 1 `bq_cli` transport | YES on Kyle's machine | **NO** (not in installed-tools) | Recipe falls through to `bq_mcp` |
| BigQuery MCP connector (`mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly`) | Recipe Step 1 `bq_mcp` transport | YES (Kyle authorized 2026-05-25) | YES | — (CSV mode for local-only fallback) |
| Notion MCP connector | `write-notion-report` Skill | YES | YES | — (Skill returns structured failure; report still saved locally per PERSIST-03) |
| `git`, `grep`, `printf`, `bash` | Recipe shell commands | YES | YES | — |
| DuckDB | (not used — see CSV engine recommendation) | n/a | n/a | n/a |

**Missing dependencies with no fallback:**
- None for Phase 3's planned scope. The cloud routine's lack of `bq` CLI is handled by the existing MCP fallback.

**Missing dependencies with fallback:**
- Cloud routine running BigQuery: uses MCP, not bq CLI. Already handled.

## Project Constraints (from CLAUDE.md + PROJECT.md)

| Constraint | Source | Phase 3 Implication |
|------------|--------|---------------------|
| No em dashes in analyzer prose | CLAUDE.md § "Voice" | Schedule.md walkthrough prose follows this. New runbook sections follow this. |
| No banned vocabulary (`leverage`, `robust`, `delve`, etc.) | CLAUDE.md § "Voice" | Same |
| No formulaic openers/closers | CLAUDE.md § "Voice" | Same |
| Public-facing repo, no secrets in committed files | CLAUDE.md project-level + PROJECT.md Constraints | `.env.example` cleanup must keep placeholders only; schedule.md walkthrough uses generic values like `your-gcp-project-id` |
| No new Python packages without explicit justification | PROJECT.md Constraints | Confirms stdlib CSV engine recommendation; DuckDB would need explicit justification (which research did not surface) |
| Tech stack — bq CLI, not Python BigQuery client | PROJECT.md Constraints | Already honored; CSV path doesn't change this for the BigQuery branch |
| No application framework (no FastAPI, Click, etc.) | PROJECT.md Constraints | CSV helper is a thin stdlib script (CONTEXT.md default); aligned |
| CHANGELOG-as-discipline (every behavior-changing edit) | docs/maintenance.md | Phase 3 will generate many entries; planner should expect a CHANGELOG diff in nearly every plan |
| Idempotency: same inputs = same report | PROJECT.md Constraints | CSV fixture seeds are stable (`Random(42)`, etc.); recipe is single-pass; satisfied |

## Sources

### Primary (HIGH confidence)
- `.claude/commands/run-analyzer.md` (recipe, 348 lines — read in full)
- `.planning/phases/01-first-notion-report-end-to-end/01-04-SUMMARY.md` (live-run verification record)
- `.planning/phases/02-honest-analyst-depth/VERIFICATION.md` (human-needed items)
- `runs/2026-05-25/summary.json` + `runs/2026-05-25/queries/*.json` (live BigQuery output shape)
- `reports/2026-05-25.md` (live Phase 1 report)
- `CHANGELOG.md` (full edit history, 2026-05-24 through 2026-05-26)
- https://code.claude.com/docs/en/routines (fetched 2026-05-26 — cloud routine UI field names)
- https://code.claude.com/docs/en/claude-code-on-the-web (fetched 2026-05-26 — installed-tools table)
- `.planning/codebase/CONCERNS.md` (tech debt inventory)
- `.planning/codebase/INTEGRATIONS.md` (data-source contract)
- `BUSINESS_RULES.md` (per-table grain, join keys)
- `CLAUDE.md` (voice + analytical contract)
- `scripts/csv_fallback_loader.py` (current 160-line loader, bug locations confirmed)

### Secondary (MEDIUM confidence)
- Phase 2 02-CONTEXT.md (D-01 through D-12 + D-07a/D-07b/D-09/D-10/D-11/D-12 references)
- `.gitignore` (confirmed Skill negation, `reports/` not ignored, `sample_data/` ignored)

### Tertiary (LOW confidence)
- None — every claim in this research is grounded in a file in the repo or an Anthropic docs page fetched today.

## Metadata

**Confidence breakdown:**
- Phase 1+2 ground truth: HIGH — verified by reading shipped files.
- CSV engine recommendation: HIGH — stdlib vs DuckDB tradeoff grounded in concrete SQL syntax differences and the shipped query files.
- Cloud routine walkthrough field names: HIGH — fetched live from claude.com docs 2026-05-26.
- Failure mode inventory: HIGH for Phase 1+2 modes (commit history is the source of truth); MEDIUM for the predicted cloud modes (#7-12), which haven't been exercised yet.
- Runbook scope: HIGH for what to add (concrete from commits + cloud docs); MEDIUM for the exact section template (existing template is Symptom/Fix/Recording; new sections should match).
- Tech debt fold-in: HIGH — each item traceable to CONCERNS.md.

**Research date:** 2026-05-26
**Valid until:** 7 days (cloud routine UI is "in research preview" per Anthropic banner; field names may rotate)

## RESEARCH COMPLETE
