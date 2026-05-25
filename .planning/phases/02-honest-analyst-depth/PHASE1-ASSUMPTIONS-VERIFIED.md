# Phase 1 Dependency Assumption Verification

**Recorded:** 2026-05-25
**Purpose:** Phase 02's Plans 02 and 03 read this file to know which Phase 1 surfaces they can rely on, without redoing the verification work. Sourced from `02-RESEARCH.md` § "Assumptions Log".

Phase 1 has shipped on `main` as of 2026-05-25 (commits `3a94b7d` → `561ac5c`). The `/run-analyzer` recipe and the `write-notion-report` Skill exist on disk; one live end-to-end run and one forced-failure run have been recorded.

---

## Assumption A1: Phase 1 ships /run-analyzer as a linear recipe with a clean draft → publish seam

**Status:** verified

**Evidence:** `.claude/commands/run-analyzer.md` exists (128 lines, dated 2026-05-25). The recipe is structured as eight explicitly numbered top-level Markdown sections (`## Step 0: Preflight` through `## Step 8: Operator message`). The draft / publish seam is clean and explicit:

- `## Step 4: Draft the report (PERSIST-01)` (lines 60–70) composes the Markdown report and writes it to `reports/{run_date}.md` and `runs/{run_date}/report.md`. The step ends at line 70.
- `## Step 5: Assemble the report dict` (lines 72–85) builds the strict 8-key dict the Skill consumes. It ends with a validation gate that refuses to invoke the Skill if any key is missing.
- `## Step 6: Invoke write-notion-report (NOTION-01..06)` (lines 87–96) is the Skill call.

Phase 02 Plan 02-02 inserts its three new steps cleanly at the seams:
- Prior-report-read step lands between Step 3 and the current Step 4 (becomes new Step 4; draft step becomes Step 5).
- Self-audit step lands between the current Step 4 (draft) and the current Step 5 (assemble dict), i.e., after the Markdown is assembled and before the dict is built.
- The explicit rule-application step is a reshape of the existing Step 4 body, not a new section.

**Impact on Plan 02/03:** Plan 02-02 can extend the recipe in place without a structural refactor of the seam; the eight-step shape accommodates three insertions and one rewrite. Two latent recipe defects surfaced during the Phase 1 live run that Plan 02-02 MUST inherit and fix before any other recipe edit ships (per `.planning/phases/01-first-notion-report-end-to-end/VERIFICATION.md` § "Phase-2 Inheritance" item 1):

1. `bq query --max_rows=10000` (line 30) is not a valid flag for `bq query` — the subcommand crashes with a Python `RecursionError` in bq's flag-suggester. Drop the flag; the default 100-row cap is fine for Phase 1 / 2 query sizes, or use `--n` for genuine overrides.
2. Positional SQL via `"$SQL"` fails when the SQL contains Unicode box-drawing characters (`─` U+2500, used in every sql/ file's header comment). Same `RecursionError`. Switch to `printf '%s' "$SQL" | bq --format=json query --use_legacy_sql=false --project_id="$BQ_PROJECT"` (stdin pipe).

Both fixes are scoped to Plan 02-02; Plan 02-01 does not touch the recipe.

---

## Assumption A2: Phase 1's Skill input contract uses a structured dict with per-finding records

**Status:** verified

**Evidence:** `.claude/skills/write-notion-report/SKILL.md` exists (186 lines, dated 2026-05-25). The Input contract section (lines 13–35) defines a strict 8-key dictionary:

- `run_date` (string `YYYY-MM-DD`)
- `data_health` (dict with `snapshot_dates` map and `stale_tables` list)
- `headline` (string)
- `working` (list of dict, each `{title, body, confidence}` where `confidence` is `"low" | "moderate" | "standard"`)
- `not_working` (list of dict, same shape)
- `patterns` (list of dict, same shape)
- `open_questions` (list of string)
- `markdown_body` (string — the full Markdown report)

Per-finding records ARE structured. However, the Skill explicitly states at line 22: "Reserved for Phase 2 enrichment; Phase 1 renders from `markdown_body` only." The Skill renders Notion blocks from the Markdown body in Phase 1, not from the structured fields. Both surfaces are available.

The `confidence` field on `working` / `not_working` / `patterns` entries is currently typed as a plain string (`"low" | "moderate" | "standard"`), not a structured `{label, n}` dict.

**Impact on Plan 02/03:** Plan 02-02 can choose either rendering path:
- (a) Continue rendering from `markdown_body` and place the `(label, n=N)` parenthetical inline in the prose (per D-07's inline-parenthetical format). The structured `confidence` field can carry the label only (string) and the `n` lives in the prose. No Skill change needed.
- (b) Migrate `confidence` to `{label, n}` and have the Skill's Phase-2 enrichment path use the structured field. Requires a Skill edit.

Default per RESEARCH.md Claude's Discretion: keep the Markdown-rendering path; render `(label, n=N)` inline in `markdown_body`; optionally migrate `confidence` to `{label, n}` for `summary.json` machine-readability without touching the Skill's render path. The string form on `working[].confidence` is forward-compatible with a future structured upgrade (the Skill ignores those fields today).

---

## Assumption A3: Phase 1's summary.json writer is additive-friendly

**Status:** verified

**Evidence:** `runs/README.md` (lines 30–63) documents the `summary.json` schema as a JSON example with prose around it, not as a closed schema with enforcement. There is no JSON-schema file in the repo, no validator, no allowed-keys list in the recipe.

The recipe (`Step 7`, lines 98–118 of `.claude/commands/run-analyzer.md`) lists the full field set the writer emits but does not gate on key presence beyond writing those it knows about. The Phase 1 live run already added two additive fields (`transport`, `notion_url`) noted in `runs/README.md` line 63 as "additive."

Additionally, the actual `runs/2026-05-25/summary.json` from Phase 1's live run contains a `warnings` field that is not in the example schema (it captured the two recipe defects). This is empirical proof that the writer accepts additive fields without complaint.

**Impact on Plan 02/03:** Plan 02-02's `prior_reports_consulted` (D-10) and Plan 02-03's `voice_audit` block are safe additive extensions. Plan 02-02 should also append both fields to `runs/README.md` in the same commit so the schema doc stays in sync with the writer (per Phase 1 VERIFICATION.md § "Phase-2 Inheritance" item 3).

---

## Assumption A5: Notion `markdown` body param preserves `(label, n=N)` parentheticals

**Status:** not-yet-shipped

**Evidence:** Phase 1's Skill renders Notion blocks explicitly via the `notion-create-pages` MCP with a constructed `children` array of typed blocks (per SKILL.md lines 82–142). It does NOT use the Notion API's `markdown` body param — it walks Markdown text line-by-line and emits `paragraph` / `heading_2` / `bulleted_list_item` / `callout` blocks with `rich_text[].text.content` set to literal text.

This means RESEARCH.md A5's concern about the Notion `markdown` API mangling inline parentheticals does NOT apply to Phase 1's actual Skill. The risk that remains: whether literal text strings like `"(moderate confidence, n=7)"` rendered as `rich_text[].text.content` survive in Notion without being auto-detected as some format. Plain parenthetical text is highly unlikely to trigger auto-formatting in Notion's renderer, but no Plan 02-03 run has happened yet to confirm.

**Impact on Plan 02/03:** No pre-mitigation needed in Phase 02. Plan 02-03's first real run is the verification. Fallback if the parenthetical mangles in the published page: Phase 1's Skill is already on the `children`-blocks path (not the `markdown` body param), so the fix surface is narrower than A5 originally anticipated — likely a small tweak to how the per-line classifier preserves trailing parentheticals on a paragraph block. Out of scope for Plan 02-01.

---

## Summary table

| ID | Status | Plan impact |
|----|--------|-------------|
| A1 | verified | Recipe seam is clean; Plan 02-02 inserts three steps + rewrites Step 4. MUST fix two recipe defects (max_rows, positional-SQL) before any other recipe edit. |
| A2 | verified | Structured per-finding dict exists; Phase 1 renders from `markdown_body` only. Plan 02-02 may keep that path and inline `(label, n=N)` in Markdown. |
| A3 | verified | `summary.json` writer is additive-friendly (empirically confirmed via `warnings` field already present). Plans 02-02 and 02-03 extend safely. |
| A5 | not-yet-shipped | Skill uses `children` blocks, not `markdown` body param, so original A5 risk is reframed. First real Plan 02-03 run confirms inline-parenthetical rendering. |
