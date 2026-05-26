# Phase 3: CSV Parity and Operational Polish - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning (depends on Phase 1 execution — see Phase Boundary)

<domain>
## Phase Boundary

Phase 3 makes the analyzer's `DATA_SOURCE=csv` path reach feature parity with the BigQuery path, hardens the weekly Monday 9am Phoenix `/schedule` routine so it can launch as a cloud routine on claude.com (not just run locally), and captures every failure mode hit during Phase 1+2 builds in `docs/runbook.md` so future runs degrade visibly rather than silently.

**In scope (6 requirements):** CSV-01, CSV-02, SCHED-01, SCHED-02, ERR-01, ERR-03.

**Out of scope:**
- Anything Phase 1 owns (HEALTH-*, BQ-*, NOTION-*, PERSIST-*, ERR-02) — Phase 1 must ship first.
- Anything Phase 2 owns (ANALYSIS-*, REPORT-*) — Phase 2 produces the analytical depth Phase 3's CSV path must mirror.
- Versioning the `/schedule` routine config in the repo — FLOW-01, v2 deferred per PROJECT.md.
- Pre-commit hooks for SQL validation — FLOW-02, v2 deferred.

**Hard ordering constraint.** Phase 3 cannot start work until Phase 1 ships `.claude/commands/run-analyzer.md` (the canonical recipe Phase 3's cloud routine setup instructs operators to paste verbatim). If Phase 3 is planned before Phase 1 executes, the planner must note that all CSV/schedule decisions assume Phase 1's slash command exists and is the single source of truth.

</domain>

<decisions>
## Implementation Decisions

> **2026-05-26 architecture correction.** D-02 (and parts of D-04) below were written under the assumption that the cloud routine's "Instructions" field is a frozen system-prompt paste-target for `.claude/commands/run-analyzer.md`. Screenshots of the live claude.com → Claude Code → Routines UI on 2026-05-26 show that's wrong: the routine has a **Repository selector** that attaches a GitHub repo to the routine, and the routine reads the repo's files at run time (including `.claude/commands/`). The Instructions field is a **short imperative prompt**, not a recipe paste. D-02 is superseded by D-02-R (below) and the Phase 3 plans that depend on it (specifically Plan 03-03's `.planning/` dereferencing work and Plan 03-03 Task 2's walkthrough) have been retargeted. D-01, D-03, and D-04's "what to verify" intent are unchanged; D-04's "what fields to fill in" was rewritten against the actual UI.

### Cloud `/schedule` Routine (focus of this discussion)

- **D-01: Cloud routine uses the BigQuery web connector for BigQuery access.** Kyle has already authorized the BigQuery MCP in his Anthropic web account (confirmed 2026-05-25). The routine system prompt uses the BigQuery MCP tools directly. **No service account JSON keys go anywhere near the routine config** — no SA key in env vars, no key rotation to track. This is symmetric with the Notion connector path already used for the cloud Notion writer. Schedule.md documents "auth the BigQuery connector once in claude.com settings" as a one-time prerequisite, not a per-run concern.

- **D-02 (SUPERSEDED — see D-02-R):** ~~`.claude/commands/run-analyzer.md` is the canonical recipe; `docs/schedule.md` instructs the operator to paste its contents into the cloud routine's system prompt. Zero risk of drift because there is only one source file. Editing the recipe means re-pasting into the routine (which is a CHANGELOG-worthy event anyway). No separate `routines/` directory, no inline duplicated block in schedule.md. The slash command file must therefore stay self-contained enough that copy-paste-into-routine is realistic (no project-local `@`-imports the cloud context cannot resolve) — this is already a Phase 1 D-06 requirement; Phase 3 verifies it.~~

- **D-02-R: `.claude/commands/run-analyzer.md` is the canonical recipe; the cloud routine attaches the `channel-patterns-analyzer` repo and Claude reads the recipe from the repo on every run.** No paste-and-resync; pushing to `main` propagates to the next routine run. The routine's **Instructions field** is a short imperative — the canonical wording is the user's existing user-story prompt:

  > Help me wrap this analyzer as a Claude Code routine that runs every Monday at 9am using /schedule. The routine should run the analyzer end-to-end — query the youtube_analytics dataset in BigQuery, run analysis, call the write-notion-report skill, write to my channel-patterns Notion page.

  Plan 03-03 Task 2's walkthrough uses this exact text as the Instructions value (or a slightly polished version). Because slash-command auto-discovery semantics in Routines are not 100% confirmed (the UI is in research preview), the walkthrough plans for both modes: (a) the imperative above + Claude finds `/run-analyzer` from `.claude/commands/`; (b) fallback — if `/run-analyzer` does not resolve, refine Instructions to explicitly reference the recipe path. The CONTEXT.md "no `@`-imports in cloud context" concern is OBSOLETE — `.planning/` paths resolve fine in the cloud routine because the repo is checked out.

- **D-03: Smoke test the routine before relying on the Monday schedule via a "Run now" checklist at the end of `docs/schedule.md`.** After completing the cloud routine setup steps, the operator clicks "Run now" in the Anthropic UI and verifies four things: (a) a new child page appears under `NOTION_REPORT_PAGE_ID` within 60s, (b) the page has all six required report sections (Data Health, Headline, What is working, What is not working, Patterns worth watching, Open questions), (c) `runs/{date}/summary.json` was written, (d) the Anthropic UI shows the run as completed (not errored). Each failure case in the checklist links to the matching `docs/runbook.md` section. No test-mode env var, no `NOTION_TEST_PAGE_ID`, no code branches for test mode — keeps the recipe single-purpose.

- **D-04 (intent preserved; field list rewritten per 2026-05-26 UI ground-truth): `docs/schedule.md` includes a step-by-step UI walkthrough with explicit field names and values for the cloud routine setup.** Numbered steps follow the actual claude.com → Claude Code → Routines → New routine form, in display order: (1) **Name** field; (2) **Instructions** field — short imperative prompt (the canonical user-story prompt from D-02-R); (3) **Select a repository** dropdown — pick `kyle-chalmers/channel-patterns-analyzer`; (4) **Select a trigger** — Schedule, Weekly, Monday, 9:00 AM, America/Phoenix; (5) **Connectors** tab — confirm Google Cloud BigQuery and Notion are attached, prune any connectors that aren't needed; (6) **Behavior** and **Permissions** tabs — defaults are fine unless the smoke test surfaces a need; (7) **Env vars** (under the environment's settings, not the top-level form): `NOTION_REPORT_PAGE_ID`, `BQ_PROJECT`, `BQ_DATASET`; (8) Click **Create**. Concrete enough that an operator following the doc top-to-bottom produces a working routine on the first try. UI labels will rot when claude.com updates the Routines UI; we accept that and add a `CHANGELOG.md` entry when a UI change forces a doc update. Invariants-only is not enough for first-launch confidence; both-walkthrough-and-invariants is over-documented for a doc one person reads twice a year.

### Claude's Discretion

The user opted to focus this discussion on getting the cloud `/schedule` routine launchable. The remaining Phase 3 gray areas are explicitly deferred to the planner / researcher with the defaults below. The planner should adopt these unless research surfaces a strong reason to revise, and should call out the revision in PLAN.md if so.

- **CSV-01 / CSV-02 execution engine.** Default: extend `.claude/commands/run-analyzer.md` to branch on `DATA_SOURCE` at the BigQuery-call step. When `DATA_SOURCE=csv`, the recipe reads the four `sample_data/*.csv` files via a thin Python stdlib helper (`scripts/csv_query.py` or similar) that returns the same JSON shape `bq query --format=json` returns. The same SQL files are NOT re-executed against CSVs (no DuckDB dependency, no sqlite import). This keeps "no new Python packages" intact (per PROJECT.md Constraints) and avoids a second SQL engine to maintain, at the cost that CSV-path analysis logic is a separate Python code path that can drift from SQL behavior. The planner should weigh the alternative — DuckDB-reads-CSV-directly — and document the tradeoff in PLAN.md before locking the choice. The CSV-path output must satisfy `runs/{date}/queries/*.json` shape parity so downstream report-drafting code does not know which source it came from.

- **CSV freshness behavior (knock-on to CSV-01).** Default: regenerate `sample_data/*.csv` on every CSV-mode run via `scripts/csv_fallback_loader.py` so the CSVs always have today's snapshot. This makes CSV-mode a happy-path demo (Data Health always passes) rather than a stale-data test harness. Operators wanting to test the stale-data code path can pass a `--snapshot-date` override to the loader (a new arg the planner should add) and re-run. Fixes the existing `date.today()` / fake-UTC bug (`scripts/csv_fallback_loader.py:55,145`) as part of the same change. A second "csv-stale" fixture set is rejected as over-engineering for a private analyzer with one operator.

- **CSV parity definition (CSV-01 success criteria reading).** Default: "structurally identical" means same six report sections in the same order, same confidence labels on any claims (using a live count from CSV-derived `video_metadata`), and same persistence artifacts (`reports/{date}.md`, `runs/{date}/summary.json`, `runs/{date}/queries/*.json`). It does NOT mean identical findings text — the CSV fixture data will produce different (and obviously not real) headlines. The Data Health section's snapshot timestamps necessarily differ. The report should include a single line at the top noting `data source: csv (sample fixtures, not live)` so a reader is never confused about whether they are looking at a real report.

- **ERR-01 runbook coverage.** Default: schedule.md's "Run now" checklist (D-03) drives the runbook expansion. Each new failure mode hit during Phase 1+2 execution and Phase 3 smoke-testing gets a named section in `docs/runbook.md` following the existing template (Symptom / Fix / Recording), with a one-line `CHANGELOG.md` entry per the maintenance doc. The slash command's failure-handling step should also include a closing instruction: "If this failure mode is not in `docs/runbook.md`, add it as part of the fix." The planner should explicitly inventory what Phase 1 + Phase 2 surfaced before declaring Phase 3 done — the existing 5 runbook sections cover bq-auth-local, stale table, missing/empty table, schema drift, and Notion write fail; cloud-side variants (BigQuery connector not authorized, Notion connector not authorized, routine env var missing, routine run timed out, Anthropic UI shows error) need their own sections under D-04's setup walkthrough.

- **ERR-03 mechanism for keeping the runbook current.** Default: manual discipline backed by the existing maintenance doc rule — adding to `docs/runbook.md` and logging in `CHANGELOG.md` is part of the fix, not a follow-up. No automated tooling, no end-of-phase forensics pass, no slash-command-driven runbook prompt. Single-operator analyzer, low velocity, low ceremony.

### Folded Todos

None — `cross_reference_todos` returned no matches for Phase 3.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Analyzer runtime contract (inherited from Phase 1)
- `CLAUDE.md` — Analyzer voice, reasoning rules, age control, sample-size thresholds, six-section report structure. Phase 3's CSV path must produce reports that satisfy this contract.
- `BUSINESS_RULES.md` — Per-table grain, join keys, data refresh expectations. CSV fixtures must respect the same grain (one row per `(video_id, snapshot_date)` for the first three tables, one row per `(video_id, snapshot_date, traffic_source_type)` for `daily_traffic_sources`).

### Requirements and scope
- `.planning/PROJECT.md` — Project framing, Constraints section (especially "no new Python packages added without explicit justification" — guides the DuckDB-vs-stdlib CSV choice).
- `.planning/REQUIREMENTS.md` — Phase 3 covers CSV-01, CSV-02, SCHED-01, SCHED-02, ERR-01, ERR-03 (6 requirements). Out of Scope section lists FLOW-01 (versioned routine config) and FLOW-02 (SQL pre-commit) as v2.
- `.planning/ROADMAP.md` §"Phase 3: CSV Parity and Operational Polish" — phase goal, requirements, success criteria.

### Phase ordering dependencies
- `.planning/phases/01-first-notion-report-end-to-end/01-CONTEXT.md` — Phase 1's locked decisions (D-01 through D-06). Especially:
  - **D-02:** slash command is one linear recipe at `.claude/commands/run-analyzer.md`. Phase 3 extends that file (does not create a parallel CSV recipe).
  - **D-03:** runtime tool-probe pattern. Phase 3 adds `DATA_SOURCE=csv` as a third branch in the same probe.
  - **D-04:** bq CLI vs BigQuery MCP at runtime. Phase 3's cloud routine path uses BigQuery MCP (D-01 in this CONTEXT.md confirms it's already authorized).
  - **D-05 / D-06:** schedule host is "both, local primary," cloud routine embeds recipe verbatim. Phase 3 operationalizes this for cloud launch.
- Phase 2's CONTEXT.md does not exist yet. Phase 3 planning should not block on it, but the planner should re-verify CSV parity once Phase 2 has shipped (in case Phase 2's analytical depth introduces new artifacts the CSV path must produce).

### Existing files Phase 3 modifies (not creates)
- `docs/schedule.md` (48 lines, conceptual) — Phase 3 expands the cloud-routine setup section per D-04. Keep the existing "What the routine does" and "Local vs. cloud" framing; add the numbered walkthrough + Run-now checklist.
- `docs/runbook.md` (90 lines, 5 named sections) — Phase 3 adds cloud-specific failure sections per ERR-01 default. Existing sections (bq auth, stale table, missing/empty table, schema drift, Notion write fail) keep their structure.
- `scripts/csv_fallback_loader.py` (160 lines) — Phase 3 fixes the `date.today()` / fake-UTC bug at `:55` and `:145`, and adds `--snapshot-date` arg per CSV freshness default.
- `sample_data/*.csv` — Phase 3 regenerates these on every CSV-mode run; they are gitignored, so no commit churn.
- `.claude/commands/run-analyzer.md` — created in Phase 1; Phase 3 extends with the CSV branch.
- `.env.example` — Phase 3 cleans up unused env vars (`YOUTUBE_CHANNEL_ID`, `ANALYSIS_LOOKBACK_DAYS`, `MIN_VIDEO_AGE_DAYS`, `SCHEDULE_TIMEZONE` per CONCERNS.md tech-debt audit) OR wires them through; planner picks.
- `CHANGELOG.md` — Phase 3 adds entries for every behavior-changing edit per the maintenance doc.

### Codebase intelligence (already shipped)
- `.planning/codebase/STRUCTURE.md` — Directory layout, naming conventions, where new files belong.
- `.planning/codebase/INTEGRATIONS.md` — External services (BigQuery, Notion), auth surfaces, env-var inventory. Confirms BigQuery web connector and Notion web connector are the cloud-routine surfaces.
- `.planning/codebase/CONCERNS.md` — Pre-existing tech debt the planner should fold into Phase 3 where it overlaps with the phase's scope. Especially: timezone bug in `sql/*.sql` (CONCERNS.md "Timezone inconsistency"), CSV loader UTC mislabeling (CONCERNS.md "CSV fallback writes timestamps relative to today"), `requirements.txt` cross-reference rot (CONCERNS.md "`requirements.txt` semantic mismatch"), unused env vars (CONCERNS.md "Unused environment variables").

### External / runtime
- Claude Code `/schedule` routines docs: https://code.claude.com/docs/en/routines — official reference linked from existing `docs/schedule.md`. Researcher should re-verify the cloud routine config schema (field names, env-var input shape, connector authorization flow) is still accurate before D-04's walkthrough is written.
- BigQuery MCP connector in Kyle's Anthropic web account — confirmed authorized 2026-05-25.
- Notion connector in Kyle's Anthropic web account — confirmed authorized (per existing `docs/schedule.md` and Phase 1 context).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`docs/schedule.md`** (48 lines) — already establishes the "local vs cloud — why the distinction matters" frame and a local/cloud comparison table. Phase 3 expands the cloud column, not the conceptual scaffolding.
- **`docs/runbook.md`** (90 lines, 5 sections) — established template per failure mode (Symptom / Fix / Recording). New sections added in Phase 3 should follow the same shape exactly. Note: existing runbook references `BUSINESS_RULES.md §5` and `§6` that do not exist (CONCERNS.md tech debt #1) — fix as part of any Phase 3 runbook edits.
- **`scripts/csv_fallback_loader.py`** (160 lines, stdlib-only) — already generates the four required CSV fixtures with stable seeds. Phase 3 reuses the generator; the only changes are (a) UTC fix at `:55, :145`, (b) `--snapshot-date` arg per CSV freshness default.
- **`sample_data/*.csv`** — fixtures exist on disk today. The same files Phase 3's CSV path reads (`daily_traffic_sources.csv`, `daily_video_analytics.csv`, `daily_video_stats.csv`, `video_metadata.csv`).

### Established Patterns
- **One linear recipe file (`.claude/commands/run-analyzer.md`).** Phase 1 D-02 establishes the slash command as a single ~80–150 line markdown recipe. Phase 3's CSV branch lives inside that file, not in a parallel command. Phase 3's cloud-routine canonical source is that same file (D-02 in this CONTEXT.md).
- **Runtime tool-probe (Phase 1 D-03).** "If `bq` is available, use it. Else BigQuery MCP." Phase 3 extends to: "If `DATA_SOURCE=csv`, read fixtures. Else, if `bq` is available, use it. Else BigQuery MCP." Three branches, one decision point.
- **No new Python packages without justification** (PROJECT.md Constraints). Argues for the stdlib CSV-reader helper default over DuckDB.
- **CHANGELOG-as-discipline** (`docs/maintenance.md`). Every behavior-changing edit gets a one-line `CHANGELOG.md` entry. Phase 3 generates many such entries; the planner should expect a `CHANGELOG.md` diff in nearly every plan.

### Integration Points
- **Slash command → CSV helper:** when `DATA_SOURCE=csv`, the recipe step that "runs the SQL files via the appropriate transport" instead invokes the CSV helper. Output JSON shape must match `bq query --format=json` so the downstream draft-report step is source-agnostic.
- **`write-notion-report` Skill (Phase 1 deliverable) → cloud Notion connector:** the same Skill must work in the cloud routine context. Phase 1 D-04 already accepts this contract; Phase 3 verifies it during smoke-testing (D-03 in this CONTEXT.md).
- **Cloud routine system prompt → `.claude/commands/run-analyzer.md` (verbatim copy):** the integration is "copy-paste at routine creation time" per D-02. There is no automated sync; that is intentional (FLOW-01 deferred to v2).
- **Failure surfacing in cloud routine:** without a terminal, errors land in the Anthropic UI's routine run history and (per Phase 1 D-02) in `runs/{date}/summary.json` written by the recipe. The Run-now checklist (D-03) verifies both surfaces are non-empty.

</code_context>

<specifics>
## Specific Ideas

- **Kyle has already authorized BigQuery MCP in his Anthropic web account** (confirmed 2026-05-25). The schedule.md walkthrough should state this as a one-time prerequisite (with a short "if you haven't yet, do this first" pointer), not as a per-routine setup step.
- **The cloud routine name should be explicit:** `channel-patterns-analyzer-weekly` (matches the repo name and signals cadence at a glance).
- **The Run-now checklist should be runnable in under 2 minutes.** If it grows past that, prune; the operator should be able to verify the routine works without scheduling a meeting with themselves.
- **Phase 3 cannot begin work until Phase 1 ships `.claude/commands/run-analyzer.md`.** The planner should explicitly note this dependency in PLAN.md and stage Phase 3 work behind Phase 1 completion. If Phase 3 is opportunistically planned before Phase 1 executes (e.g., to surface Phase 1 gaps early), the plan must be re-validated against the actual Phase 1 recipe once it lands.
- **Phase 3 is the natural place to consolidate tech debt** the codebase audit surfaced (`.planning/codebase/CONCERNS.md`): timezone inconsistency in SQL, unused env vars in `.env.example`, `requirements.txt` cross-reference rot, BUSINESS_RULES.md section-number drift. The planner should fold these into Phase 3 plans where they overlap with the phase's scope (e.g., env-var cleanup naturally rides along with SCHED-01's walkthrough; section-number drift fixes naturally ride along with ERR-01's runbook expansion).

</specifics>

<deferred>
## Deferred Ideas

- **CSV execution engine deep-dive.** User chose not to discuss; default in `Claude's Discretion` above. If the researcher surfaces evidence that a DuckDB-reads-CSV approach is materially cleaner, the planner can re-open this with Kyle before locking the plan.
- **CSV freshness as a test harness.** Default treats CSV as happy-path demo. If, after Phase 2 ships, Kyle wants to use CSV mode to exercise stale-data and missing-table code paths, that becomes a Phase 4 (v2) item — `RICH-*` or a new `CSV-TEST-*` requirement.
- **Test-mode env var for routine smoke-testing.** Considered, rejected for now. If smoke-testing becomes a routine pattern (not a one-time setup activity), revisit with `ROUTINE_TEST_MODE` + `NOTION_TEST_PAGE_ID`.
- **Versioning `routine_config.json` in the repo (FLOW-01).** Explicitly v2 per PROJECT.md / REQUIREMENTS.md. Phase 3 does not own this.
- **End-of-phase forensics pass for runbook coverage.** Considered, rejected in favor of manual discipline (the existing maintenance doc rule already covers this).

</deferred>

---

*Phase: 3-CSV Parity and Operational Polish*
*Context gathered: 2026-05-25*
