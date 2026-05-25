# Phase 2: Honest Analyst Depth - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 wires the analytical contract (`CLAUDE.md` + `BUSINESS_RULES.md`) into the analyzer's reasoning and report output, so the published report would actually pass Kyle's bar without manual rewriting. Phase 1 ships the orchestration plumbing (run trigger, BigQuery transport, Notion Skill, persistence, data-health check) and a minimal report with placeholders. Phase 2 fills in the depth: age-controlled comparisons, confidence labels next to every claim, full six-section structure, prior-report calibration, and voice-rule enforcement.

In-scope this phase: ANALYSIS-01..05, REPORT-01..03 (8 requirements). Out-of-scope: CSV parity (Phase 3), `/schedule` documentation (Phase 3), runbook expansion for new failure modes (Phase 3), and anything that adds new analytical *capabilities* beyond the rules already in `CLAUDE.md` (those belong in v2).

**Phase 1 dependency note:** Phase 1 was being researched/planned in parallel when this context was captured. Decisions below assume Phase 1 lands as scoped in `01-CONTEXT.md`: `/run-analyzer` slash command at `.claude/commands/run-analyzer.md`, `write-notion-report` Skill that accepts a structured report dict, data-health check as the first run step, default report depth of "Data Health + Headline + one What's working finding" with other sections present as labeled placeholders. If any of those assumptions break, revisit decisions D-04 (recipe extension point) and D-08 (placeholder replacement strategy) before planning.

</domain>

<decisions>
## Implementation Decisions

### Rule Enforcement Mechanism

- **D-01: Two-layer enforcement, both in markdown.** Layer 1: the `/run-analyzer` recipe explicitly re-references the relevant `CLAUDE.md` sections at draft time (e.g., "Apply the age-control rule in `CLAUDE.md` § 'Age control is non-negotiable' before listing top performers"). Layer 2: a final **self-audit step** added to the recipe, run after the draft is assembled and before invoking `write-notion-report`. The self-audit checks the draft against a concrete checklist (em dashes, banned vocabulary, formulaic openers, every pattern claim carrying a confidence label, age-control exclusions applied to top performers, six sections present in order, stale-table disclaimers where applicable) and fixes violations inline. Rationale: matches PROJECT.md's constraint of "no application framework — new code only when a markdown rule can't express the behavior." The fragility CONCERNS.md flagged (zero enforcement today) is addressed without introducing a new Skill or Python checker.
- **D-02: No separate voice-checker Skill.** Rejected. Adds infrastructure surface area that the project's "AI analyst, not Python orchestrator" framing explicitly avoids, and the self-audit step expresses the same behavior in markdown.
- **D-03: No new `docs/voice-and-rules-checklist.md` file.** Rejected to avoid duplication drift with `CLAUDE.md`. The self-audit checklist lives inline in the recipe and references `CLAUDE.md` sections by name, not by section number (per CONCERNS.md's section-numbering-drift warning).
- **D-04: Self-audit is a recipe step, not a Skill invocation.** The recipe extends Phase 1's `/run-analyzer` flow by inserting one new step between "Draft report" and "Invoke `write-notion-report`". Planner: confirm Phase 1's recipe has a clean extension point at this boundary; if Phase 1's recipe wires draft → publish too tightly, refactor that seam as part of Phase 2.

### SQL Fix Scope

- **D-05: Fix the age-control SQL bugs as part of Phase 2.** Phase 2's analytical correctness rides on these queries, so deferring the fixes to Phase 3 ("operational polish") would mean Phase 2 ships demonstrably wrong numbers. Specifically:
  - Replace bare `CURRENT_DATE()` with `CURRENT_DATE("America/Phoenix")` in `sql/02_top_full_length_videos.sql`, `sql/03_age_controlled_performance.sql`, and `sql/04_data_health_check.sql` (CONCERNS.md "Timezone inconsistency in SQL").
  - Switch the `MAX(snapshot_date)` filter in `sql/02` and `sql/03` from "video_metadata's latest" to a "latest common snapshot across `video_metadata` + `daily_video_stats`" pattern (CONCERNS.md "days_since_published uses snapshot table's MAX(snapshot_date) to filter the metadata side only"). Borrow the `LEAST(...)` pattern from `sql/01` and extend it to the actually-joined tables.
  - Either remove `LIMIT 20` from `sql/02` and `sql/03`, or derive the limit from `video_count_full_length` so the long tail isn't silently dropped as the channel grows. Default: remove the limit (dataset is small; Phase 2's age-control filter will already narrow the set).
  - Log each SQL change as a one-line `CHANGELOG.md` entry per `docs/maintenance.md`.
- **D-06: Out of scope for Phase 2 SQL work.** Hardcoded `youtube_analytics` dataset templating (that's BQ-01, owned by Phase 1). `BUSINESS_RULES.md` section-numbering drift in SQL header comments (cosmetic; rolls into Phase 3's docs polish unless trivially fixed in the same commit). `sql/01`'s two-table `LEAST(...)` extension to four tables (Phase 2 doesn't depend on `sql/01`; Phase 3 can handle it as part of CSV parity work).

### Confidence Label Format

- **D-07: Inline parenthetical with sample size next to every pattern claim.** Format: `(low | moderate | standard confidence, n=N)` where `N` is the count of *eligible* videos in the comparison set (i.e., the live `video_metadata` count minus age-excluded videos). Example: `"VID042 'GraphQL vs REST' got 4,300 views in its first 30 days, ~5× the channel median of 860 (standard confidence, n=18)."` For findings rendered as tables, add `Confidence` and `n` columns rather than inlining in cell text. Rationale: keeps the label in plain sight per `CLAUDE.md`, preserves the no-em-dash voice rule (parenthetical, not dash-clause), works in both markdown and whatever blocks `write-notion-report` produces, and exposes `n` so the reader can sanity-check the hedging without trusting the label alone.
- **D-07a: Single claim, single label.** Per-section header blocks rejected — different claims in the same section can have different sample sizes, and a section-level label hides that. Label rides with the claim it qualifies.
- **D-07b: No Notion-specific callout for confidence.** Notion callouts are reserved for the data-health flags already established in Phase 1. Confidence labels render as plain text through whatever Notion blocks the Skill emits — no special Skill behavior required.

### Prior-Report Calibration

- **D-08: Hybrid — internal memory for calibration, no surface "as we said last week" reference.** The analyzer reads the three most recent `reports/{date}.md` files at draft time to (a) upgrade or downgrade confidence labels as the sample grows or a pattern persists, (b) avoid restating findings verbatim, and (c) notice regressions. None of that reading produces a "last week" sentence in the published report — the standalone-tone rule in `CLAUDE.md` ("assume Kyle has not seen the previous week's report") holds.
- **D-09: Cross-week patterns may be surfaced when the multi-week framing stands on its own.** When a pattern has held across multiple runs, the analyzer may include it in "Patterns worth watching" with framing that doesn't require the reader to know what last week said. Example allowed: `"For the third consecutive week, tool-specific tutorials are pulling 4×+ the views of conceptual videos (standard confidence, n=18)."` Example banned: `"As we noted last week, ..."`.
- **D-10: `summary.json` records which prior reports were consulted.** Add a `prior_reports_consulted: ["2026-05-17", "2026-05-10", "2026-05-03"]` field to the per-run `summary.json` schema. Audit trail; lets a future investigator see which prior context shaped a given report. Planner: confirm with Phase 1 whether the `summary.json` schema is locked there; if so, extend rather than redefine.

### Empty-Section and Stale-Data Handling

- **D-11: Six-section structure is contractual — never silently skip a section.** When a section legitimately has no material this week, the heading still renders, and the body says explicitly what's missing and why (e.g., `"Nothing material to report this week."` or `"Patterns analysis unavailable: daily_video_analytics is 89 days stale (see Data Health)."`). No padding with weak findings to fill a section; no silent omission.
- **D-12: Stale-table downstream impact is named in the dependent section, not just Data Health.** Per `CLAUDE.md` § "Report structure": if a downstream section depends on a stale table, it must say so. Phase 2 makes this concrete — any finding or attempted finding in "What is working", "What is not working", or "Patterns" that would have drawn from a stale table is replaced with a one-line disclaimer pointing to the Data Health entry. No silent computation against stale data.

### Claude's Discretion

The user opted to defer all four discussion areas with "whatever you recommend, I don't really care." Defaults captured above are the recommendations. Specific sub-decisions the planner and researcher may resolve with sensible defaults:

- **Exact wording of the self-audit checklist step** in the recipe — researcher should look at the current `CLAUDE.md` voice and rules sections and produce a checklist that mirrors them 1:1, so a future `CLAUDE.md` edit can be reflected by re-deriving the checklist rather than maintaining a parallel list.
- **Whether `confidence` is rendered as a string or a structured field** in the `summary.json` per-finding record (if Phase 1's Skill input contract includes per-finding records). Default: structured `{"label": "moderate", "n": 7}` for machine readability, with the prose form derived for the markdown body.
- **Whether the self-audit step gets its own JSON dump** in `runs/{date}/queries/` (it's not a query) or lives in `summary.json` as a `voice_audit: {checks_passed: [...], fixes_applied: [...]}` block. Default: extend `summary.json`; don't add a new artifact type.
- **Whether to write a small acceptance script** (bash or stdlib Python) that grep-checks generated reports for the banned vocabulary list and em dashes. Default: no, the self-audit step is the enforcement; an external grep is duplicate insurance that Phase 2 can ship without. Revisit if reports drift in practice.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Analyzer runtime contract
- `CLAUDE.md` — Voice rules, age control, sample-size thresholds, report structure, prior-report calibration rule. Phase 2 makes these executable; do not paraphrase, reference by section name.
- `BUSINESS_RULES.md` — §3 Data health expectations (Phoenix timezone), §4 Table grain + join keys. `@`-imported by `CLAUDE.md`.

### Requirements and scope
- `.planning/PROJECT.md` — Constraint that the analyzer is markdown + bq CLI + Skills, not a Python framework. Out-of-scope list rules out web UI, causal inference, cross-channel benchmarking.
- `.planning/REQUIREMENTS.md` — ANALYSIS-01..05 and REPORT-01..03 are Phase 2's mapped requirements (see traceability table).
- `.planning/ROADMAP.md` § "Phase 2: Honest Analyst Depth" — phase goal, requirements, five success criteria.
- `.planning/phases/01-first-notion-report-end-to-end/01-CONTEXT.md` — Phase 1's run-trigger decisions, default report depth, and Notion Skill input contract assumptions that Phase 2 builds on.

### SQL pattern library (existing — to be modified in Phase 2 per D-05)
- `sql/02_top_full_length_videos.sql` — Top-N source for "What is working." Phase 2 fixes the Phoenix-time + snapshot-join bugs here.
- `sql/03_age_controlled_performance.sql` — The age-controlled comparison that Phase 2's report draft draws from. Same Phoenix-time + snapshot-join fixes apply.
- `sql/04_data_health_check.sql` — Untouched by analysis depth, but the Phoenix-time fix lands here too as part of D-05.

### Persistence and audit trail
- `runs/README.md` — `summary.json` schema. Phase 2 extends with `prior_reports_consulted: [...]` (D-10) and optionally `voice_audit: {...}` (Claude's Discretion).
- `reports/README.md` — Confirms the "analyzer reads its own prior runs to calibrate confidence" rule that ANALYSIS-05 and D-08 implement.

### Codebase intelligence (read before planning)
- `.planning/codebase/CONCERNS.md` — Names the specific SQL bugs Phase 2 addresses (timezone, snapshot-join, LIMIT 20), flags the rule-enforcement fragility that D-01 solves, and warns about section-numbering drift.
- `.planning/codebase/STRUCTURE.md` § "Where to Add New Code" — Conventions for SQL header comments, CHANGELOG entries, and the no-new-deps rule that applies to D-05's SQL edits.
- `.planning/codebase/CONVENTIONS.md` — General codebase conventions the planner should respect.

### Maintenance protocol
- `docs/maintenance.md` § "Evolving a business rule" — Required CHANGELOG.md entry pattern for D-05's SQL changes and any rule-enforcement additions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`CLAUDE.md` § "Brutal honesty about underperformance" + § "Age control is non-negotiable" + § "Small samples get hedged, every time" + § "Never claim what the data does not support"** — The analytical contract is already written. Phase 2's job is wiring, not authoring. The self-audit checklist (D-01) is derived from these sections.
- **`CLAUDE.md` § "Report structure"** — Six-section order, prior-report calibration rule ("read the most recent 3-4 entries"), and the standalone-tone constraint that D-08 implements.
- **`sql/03_age_controlled_performance.sql`** — Already implements the `>= 14 days` filter and the views-per-day proxy. The query is right in spirit; Phase 2's D-05 fixes its bugs without rewriting it.
- **`reports/README.md` analyzer-memory rules** — Already states "the archive is the analyzer's memory, not the reader's." D-08 is just an enforcement of an already-documented rule.

### Established Patterns
- **`@`-imports in `CLAUDE.md`** — Phase 1's `/run-analyzer` recipe already inherits `CLAUDE.md` via `@`-import (per Phase 1 D-02 / D-04 context). Phase 2's self-audit step references `CLAUDE.md` sections by name, leveraging the same import.
- **Reference rules by section title, not section number** — CONCERNS.md flagged section-numbering drift across `CLAUDE.md`, SQL header comments, runbook, and maintenance. Phase 2 must not introduce new `BUSINESS_RULES.md §N` references; use the section title.
- **CHANGELOG.md entries are mandatory for behavior-changing SQL or rule edits** — Per `docs/maintenance.md`. D-05's three SQL fixes each get a one-line entry.
- **No new Python deps** — `requirements.txt` rule in PROJECT.md. Phase 2 should not need any.

### Integration Points
- **`/run-analyzer` recipe → self-audit step → `write-notion-report` Skill.** Phase 2 inserts the self-audit between the existing draft and publish steps. Planner: verify Phase 1's recipe boundary is clean enough to extend at this point without refactor; if not, refactor the seam in Phase 2.
- **Recipe draft step → SQL files.** Phase 2's SQL changes (D-05) flow through unchanged: the recipe still executes the same files; they just produce correct numbers now.
- **Recipe draft step → `reports/{date}.md` reads.** D-08's prior-report calibration is a new read pattern at the start of the draft step. No new files; existing `reports/` archive is the source.
- **Self-audit step → `summary.json`.** Optional `voice_audit` block (Claude's Discretion in `decisions`); planner decides whether to add or skip.

### Code-context risks the planner should hold
- **Phase 1 is in flight.** Some Phase 1 decisions affect Phase 2's planning. If Phase 1's Skill input contract changes (Claude's Discretion in `01-CONTEXT.md`), the per-finding confidence field format (D-07) may need to adapt.
- **89-day-stale `daily_video_analytics`.** Real production condition right now. The first Phase 2 run will exercise D-11 and D-12 (stale-table disclaimers) immediately; planner should make this a verification target, not just a paper rule.
- **~24 full-length videos and falling-eligible after the 14-day filter.** Most pattern claims this phase produces will land in the "low confidence (small sample)" or "moderate confidence" band per `CLAUDE.md`. That's not a bug; that's the channel's reality. The label exists precisely to make this visible.

</code_context>

<specifics>
## Specific Ideas

- **The 89-day-stale `daily_video_analytics` table** is the natural integration test for D-11 and D-12. Phase 2's first real run should produce a report where the Patterns section explicitly disclaims missing traffic-source and watch-time analysis instead of silently going quiet. Planner: include this as a verification scenario.
- **Banned vocabulary list lives in two places already** — global `~/.claude/CLAUDE.md` ("Prose & Anti-AI-Voice" section) and project `CLAUDE.md` ("Voice" section). The self-audit checklist should reference the project `CLAUDE.md` version (it's the project-specific list); the planner does not need to merge the two.
- **The five Phase 2 success criteria from ROADMAP.md are the acceptance gate.** They map cleanly to D-05 (SC1: age-controlled comparisons), D-07 (SC2: confidence labels next to claims, derived from live count), D-11/D-12 (SC3: six sections with inline context), D-08 (SC4: prior-report calibration), D-01 (SC5: voice rules pass). Planner should map plan tasks back to these for traceability.

</specifics>

<deferred>
## Deferred Ideas

- **Automated grep-based voice check** (CI step that fails on em dashes or banned vocab in `reports/*.md`) — Claude's Discretion in decisions; deferred to v2 if reports drift in practice. Captured here so it's not lost.
- **Per-section confidence summary block** at the top of each section — explicitly rejected in D-07a; captured here in case Kyle wants to revisit after seeing a few real reports.
- **Notion callout for confidence labels** — explicitly rejected in D-07b; the Notion callouts are reserved for stale-data flags from Phase 1.
- **"Follow-ups from prior reports" subsection** — explicitly rejected in D-08; the standalone-tone rule forbids it. Patterns may surface multi-week claims when self-contained (D-09), but a dedicated "follow-ups" section would import last-week context the reader doesn't have.
- **JSON schema validation for `summary.json`** — captured in CONCERNS.md as a fragile-areas item. Out of scope for Phase 2; would be a v2 hardening pass.
- **`sql/01_latest_snapshot_overview.sql` extension to four tables** — captured in CONCERNS.md. Phase 2 doesn't depend on `sql/01`; deferred to Phase 3 or v2.
- **`BUSINESS_RULES.md` section-numbering drift fix across SQL header comments and docs/runbook** — cosmetic; deferred to Phase 3's documentation polish unless trivially fixed in the same commit as D-05.
- **Templating `MIN_VIDEO_AGE_DAYS` and `BQ_DATASET` through SQL** — Phase 1 BQ-01 territory for dataset; `MIN_VIDEO_AGE_DAYS` templating deferred to v2 since the 14-day rule is hardcoded in `CLAUDE.md` too and not under tension yet.
- **LLM-as-judge eval of generated reports against `CLAUDE.md` rules** — CONCERNS.md flagged this as the highest-leverage test for this repo. Phase 2's self-audit step is a lightweight version of the same idea (run by the same Claude session that drafted the report). A separate eval pass with a fresh model session would be v2 hardening; captured here.

</deferred>

---

*Phase: 2-Honest Analyst Depth*
*Context gathered: 2026-05-24*
