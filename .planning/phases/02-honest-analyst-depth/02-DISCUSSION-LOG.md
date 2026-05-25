# Phase 2: Honest Analyst Depth - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-24
**Phase:** 2-Honest Analyst Depth
**Areas discussed:** Rule enforcement mechanism, SQL fix scope, Confidence label format, Prior-report calibration

**Session note:** Phase 1 was being researched/planned in parallel in another session. Kyle invoked Phase 2 discussion to get ahead. All four gray areas were presented; Kyle responded "Whatever you recommend, I don't really care" — defaults captured in CONTEXT.md were chosen by Claude based on existing project constraints (markdown-first analyzer, no new application framework, brutal-honesty + no-hype voice rules, public-facing repo).

---

## Rule Enforcement Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Trust the prompt | CLAUDE.md is read every run; rely on prompt-engineering alone | |
| Two-layer: recipe references + self-audit step | Recipe re-references CLAUDE.md sections at draft time, plus a self-audit step before publish | ✓ |
| Separate voice-checker Skill | Dedicated Skill that runs before write-notion-report | |
| Dedicated rules-checklist doc | New `docs/voice-and-rules-checklist.md` referenced by the recipe | |

**User's choice:** Deferred to Claude.
**Notes:** Default chosen matches PROJECT.md's "no application framework — new code only when a markdown rule can't express the behavior" constraint. CONCERNS.md flagged the absence of any enforcement as the highest fragility; the self-audit step addresses it without adding infrastructure surface area. Rejected the separate Skill (infra surface) and the new checklist doc (duplication-drift risk with CLAUDE.md).

---

## SQL Fix Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Fix in Phase 2 | Phoenix-time + snapshot-join + LIMIT-20 fixes land with Phase 2 | ✓ |
| Defer to Phase 3 | Treat as "operational polish" and ship Phase 2 over the existing buggy SQL | |
| Markdown-only compensation | Have the analyzer mentally correct for the bugs; don't touch SQL | |

**User's choice:** Deferred to Claude.
**Notes:** Phase 2's success criteria require age-controlled comparisons — shipping with the bugs means Phase 2 ships demonstrably wrong numbers. The fixes are small (3-4 SQL files, ~10 lines total). Markdown-only compensation rejected because it hides the bug instead of fixing it and violates the no-silent-drift principle in CLAUDE.md. Dataset-name templating (BQ-01) and `sql/01`'s four-table extension are explicitly carved out as not-Phase-2 work.

---

## Confidence Label Format

| Option | Description | Selected |
|--------|-------------|----------|
| Inline parenthetical with sample size | `(moderate confidence, n=7)` next to each claim | ✓ |
| Inline phrase | `based on 7 videos — moderate confidence` | |
| Per-section header block | One label at the top of each section | |
| Notion callout block | Special block type that renders differently in Notion | |

**User's choice:** Deferred to Claude.
**Notes:** Parenthetical chosen because it (a) keeps the label in plain sight per CLAUDE.md, (b) preserves the no-em-dash voice rule (the inline-phrase option requires an em dash), (c) exposes `n` so the reader can sanity-check the hedging, (d) renders identically in markdown and whatever Notion blocks the Skill emits. Per-section header rejected because claims in the same section can have different sample sizes. Notion callout rejected because callouts are reserved for stale-data flags per Phase 1.

---

## Prior-Report Calibration Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Pure internal memory | Read prior reports for calibration; never reference them in prose | |
| Structured "Follow-ups from prior weeks" subsection | Explicit cross-week reference section | |
| Hybrid: memory + self-contained multi-week framing where it stands alone | Internal memory for calibration; multi-week claims only when self-contained; summary.json records what was read | ✓ |
| Logged in summary.json only | Audit trail without behavior impact | |

**User's choice:** Deferred to Claude.
**Notes:** Hybrid chosen to honor the standalone-tone rule in CLAUDE.md ("assume Kyle has not seen the previous week's report") while still capturing the cross-week calibration value of ANALYSIS-05. "Follow-ups" subsection rejected because it would import context the reader doesn't have. Pure memory loses the upside of patterns that genuinely held across weeks. Audit-only in summary.json doesn't deliver ANALYSIS-05's intent. The hybrid captures all three: confidence tuning, restated-finding avoidance, and durable patterns (when self-contained).

---

## Claude's Discretion

The user deferred all four selected areas to Claude. Within each captured decision, the planner and researcher have additional discretion documented in CONTEXT.md `<decisions>` § "Claude's Discretion":

- Exact wording of the self-audit checklist step in the recipe.
- Whether `confidence` is rendered as a string or `{label, n}` struct in summary.json per-finding records.
- Whether the self-audit step writes its own JSON dump or extends summary.json with a `voice_audit` block.
- Whether to ship a separate grep-based acceptance script alongside the self-audit step (default: no).

## Deferred Ideas

Captured in CONTEXT.md `<deferred>`. Key items:

- Automated grep-based voice check (CI step) — v2 if reports drift.
- Per-section confidence summary block — rejected in D-07a; revisit after real-report feedback.
- Notion callout for confidence labels — rejected in D-07b.
- "Follow-ups from prior reports" subsection — rejected in D-08.
- JSON schema validation for summary.json — v2 hardening.
- `sql/01_latest_snapshot_overview.sql` four-table extension — Phase 3 or v2.
- BUSINESS_RULES.md section-numbering drift across SQL header comments and docs — Phase 3 docs polish.
- Templating `MIN_VIDEO_AGE_DAYS` and `BQ_DATASET` through SQL — Phase 1 (dataset) and v2 (age threshold).
- LLM-as-judge eval of generated reports against CLAUDE.md rules — v2 hardening.
