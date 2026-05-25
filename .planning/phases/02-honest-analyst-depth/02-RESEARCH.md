# Phase 2: Honest Analyst Depth - Research

**Researched:** 2026-05-25
**Domain:** Markdown-driven analyzer reasoning (age control, hedging, voice enforcement), BigQuery SQL correctness, Notion publishing surface
**Confidence:** HIGH (all key technical claims verified against authoritative sources; remaining LOW areas are flagged and asked, not assumed)

## Summary

Phase 2 is wiring, not authoring. The analyzer's analytical rules, voice, six-section structure, and prior-report calibration are already documented in `CLAUDE.md` + `BUSINESS_RULES.md`. What's missing is mechanical enforcement at draft time. Phase 2 ships that enforcement as markdown — extending Phase 1's `/run-analyzer` recipe at three seams: a pre-draft prior-report read, an explicit rule-application step during draft, and a self-audit pass before invoking `write-notion-report`. No new code, no new Skills, no new Python dependencies.

The analytical correctness of the report also depends on three small SQL fixes (timezone, snapshot-join, LIMIT) that CONCERNS.md flagged as bugs. Phase 2 fixes them in place because deferring would mean Phase 2 ships visibly wrong numbers. Each fix gets a one-line `CHANGELOG.md` entry per `docs/maintenance.md` § "Evolving a business rule".

The first real Phase 2 run will exercise the stale-table disclaimer machinery immediately: `daily_video_analytics` and `daily_traffic_sources` have both been 89 days stale at planning time, so multiple "Patterns" findings will land as disclaimers rather than analysis. Treat that as an integration test, not a failure mode.

**Primary recommendation:** Extend Phase 1's recipe in place with three new steps (prior-report read, explicit-rule-application step, self-audit checklist), fix the three SQL bugs as scoped under D-05, and extend `summary.json` with `prior_reports_consulted` and a `voice_audit` block. No SKILL, no Python, no new files outside the SQL touch-ups and a CHANGELOG.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Rule enforcement mechanism**
- **D-01: Two-layer enforcement, both in markdown.** Layer 1: the `/run-analyzer` recipe explicitly re-references the relevant `CLAUDE.md` sections at draft time. Layer 2: a final **self-audit step** added to the recipe, run after the draft is assembled and before invoking `write-notion-report`, checking em dashes, banned vocabulary, formulaic openers, every pattern claim carrying a confidence label, age-control exclusions applied to top performers, six sections present in order, and stale-table disclaimers where applicable.
- **D-02: No separate voice-checker Skill.** Rejected.
- **D-03: No new `docs/voice-and-rules-checklist.md` file.** The self-audit checklist lives inline in the recipe and references `CLAUDE.md` sections by name, not by section number.
- **D-04: Self-audit is a recipe step, not a Skill invocation.** Planner: confirm Phase 1's recipe has a clean extension point between "Draft report" and "Invoke `write-notion-report`"; refactor if not.

**SQL fix scope**
- **D-05: Fix the age-control SQL bugs as part of Phase 2.**
  - Replace bare `CURRENT_DATE()` with `CURRENT_DATE("America/Phoenix")` in `sql/02_top_full_length_videos.sql`, `sql/03_age_controlled_performance.sql`, and `sql/04_data_health_check.sql`.
  - Switch the `MAX(snapshot_date)` filter in `sql/02` and `sql/03` from "video_metadata's latest" to a "latest common snapshot across `video_metadata` + `daily_video_stats`" pattern, borrowing the `LEAST(...)` pattern from `sql/01`.
  - Remove `LIMIT 20` from `sql/02` and `sql/03` (default; dataset is small).
  - Log each SQL change as a one-line `CHANGELOG.md` entry per `docs/maintenance.md`.
- **D-06: Out of scope.** Hardcoded `youtube_analytics` dataset templating (BQ-01, Phase 1). `BUSINESS_RULES.md` section-numbering drift in SQL header comments (Phase 3 unless trivially fixed in the same commit). `sql/01`'s two-table → four-table `LEAST(...)` extension (Phase 3 or v2).

**Confidence label format**
- **D-07: Inline parenthetical with sample size next to every pattern claim.** Format: `(low | moderate | standard confidence, n=N)` where `N` is the count of *eligible* videos in the comparison set (live `video_metadata` count minus age-excluded videos). For findings rendered as tables, add `Confidence` and `n` columns rather than inlining in cell text.
- **D-07a: Single claim, single label.** Per-section header blocks rejected.
- **D-07b: No Notion-specific callout for confidence.** Notion callouts are reserved for the data-health flags already established in Phase 1.

**Prior-report calibration**
- **D-08: Hybrid — internal memory for calibration, no surface "as we said last week" reference.**
- **D-09: Cross-week patterns may be surfaced when the multi-week framing stands on its own.** Allowed: `"For the third consecutive week, ..."`. Banned: `"As we noted last week, ..."`.
- **D-10: `summary.json` records which prior reports were consulted.** Add `prior_reports_consulted: ["2026-05-17", "2026-05-10", "2026-05-03"]`. Planner: confirm with Phase 1 whether `summary.json` schema is locked there; extend rather than redefine.

**Empty-section and stale-data handling**
- **D-11: Six-section structure is contractual — never silently skip a section.** Heading still renders; body says explicitly what's missing and why. No padding, no silent omission.
- **D-12: Stale-table downstream impact is named in the dependent section, not just Data Health.** Any would-be finding drawing from a stale table is replaced with a one-line disclaimer pointing to the Data Health entry. No silent computation against stale data.

### Claude's Discretion

The user deferred all four discussion areas with "whatever you recommend, I don't really care." Researcher / planner defaults:

- **Self-audit checklist wording** — mirrors `CLAUDE.md` voice + rules sections 1:1, so a future `CLAUDE.md` edit can be reflected by re-deriving the checklist.
- **`confidence` field shape in per-finding records** — structured `{"label": "moderate", "n": 7}` for machine readability; prose form derived for the markdown body.
- **Self-audit artifact location** — extend `summary.json` with `voice_audit: {checks_passed: [...], fixes_applied: [...]}`; don't add a new artifact type.
- **External grep-based voice check (CI step)** — skip for Phase 2; revisit if reports drift in practice.

### Deferred Ideas (OUT OF SCOPE)

- Automated grep-based voice check (CI step that fails on em dashes / banned vocab in `reports/*.md`).
- Per-section confidence summary block at the top of each section (rejected in D-07a).
- Notion callout for confidence labels (rejected in D-07b).
- "Follow-ups from prior reports" subsection (forbidden by standalone-tone rule; D-08).
- JSON schema validation for `summary.json` (v2 hardening).
- `sql/01_latest_snapshot_overview.sql` extension to four tables (Phase 3 or v2).
- `BUSINESS_RULES.md` section-numbering drift fix across SQL header comments and docs (Phase 3 doc polish unless trivially fixed in same commit as D-05).
- Templating `MIN_VIDEO_AGE_DAYS` and `BQ_DATASET` through SQL (v2; 14-day rule is hardcoded in `CLAUDE.md` too).
- LLM-as-judge eval of generated reports with a fresh model session (v2 hardening; Phase 2's self-audit is a lightweight version).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANALYSIS-01 | Exclude `days_since_published < 14` from top performers / pattern claims | SQL bug fix (D-05) ensures the 14-day filter actually fires off `CURRENT_DATE("America/Phoenix")`; self-audit step verifies no excluded video appears in "What is working" |
| ANALYSIS-02 | Cross-age comparisons normalize to comparable window (first-30-day or labeled proxy) | `sql/03` already produces `views_per_day_since_publish_proxy`; report draft step instructs analyzer to label the proxy explicitly per the SQL header comment |
| ANALYSIS-03 | Live video count queried each run; confidence label appended next to every pattern claim | Eligible-count query pattern (below); confidence-label derivation from CLAUDE.md thresholds (`<5` low, `5–10` moderate, `≥10` standard); self-audit checks every claim carries the label |
| ANALYSIS-04 | Trending claims require ≥14 days of data per video in comparison set | Same age filter as ANALYSIS-01; self-audit checklist item covers it |
| ANALYSIS-05 | Read 3 most recent `reports/{date}.md` before drafting; calibrate confidence; avoid restating verbatim | Pre-draft recipe step reads lexicographic top-3 from `reports/`; `summary.json` records which 3 were consulted (D-10); D-08/D-09 govern what may surface |
| REPORT-01 | Six sections in order: Data Health, Headline, What is working, What is not working, Patterns worth watching, Open questions | Recipe section-skeleton template; D-11 governs empty-section handling; self-audit verifies presence + order |
| REPORT-02 | Findings include numbers, age context, confidence labels in plain sight | D-07 inline-parenthetical format; D-07-aware table format with `Confidence` and `n` columns; self-audit verifies every claim carries number + age + label |
| REPORT-03 | Voice rules enforced — no em dashes, no banned vocabulary, no formulaic openers/closers, first-person plural where it fits | Self-audit checklist mirrors `CLAUDE.md` § Voice; both em dash (U+2014) and en dash (U+2013) flagged; banned-vocab list cited from `CLAUDE.md` (not the global one) |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Age filter (`days_since_published >= 14`) | SQL (`sql/03`, new variant of `sql/02`) | — | Pushdown to the query is correct; the analyzer shouldn't filter rows it never needed to receive |
| `LEAST(...)` latest-common-snapshot | SQL | — | Per-row alignment must happen in the database, not in the analyzer's reasoning |
| Confidence label derivation | Analyzer (Claude Code session) | SQL (only to supply eligible-count input) | Threshold table lives in `CLAUDE.md`; analyzer applies it; SQL only needs to expose `eligible_count` |
| Prior-report calibration | Analyzer | Filesystem (`reports/`) | Three-file read at draft time; lexicographic sort is correct since names are `YYYY-MM-DD.md` |
| Six-section structure rendering | Analyzer (draft step) | `write-notion-report` Skill (markdown→Notion translation) | Analyzer owns the markdown report shape; Skill owns the Notion block translation |
| Self-audit / voice enforcement | Analyzer (audit step) | — | No external linter; checklist is markdown the same session executes |
| Stale-table disclaimer | Analyzer (draft step) | SQL (only to supply staleness signal via `sql/04`) | Disclaimer is prose; the staleness signal comes from Data Health |
| Persistence (`reports/`, `summary.json` voice_audit + prior_reports_consulted) | Analyzer | Phase 1 recipe (already writes these) | Phase 2 extends the existing writes; no new artifact types |

## Standard Stack

### Core
| Library / Tool | Version | Purpose | Why Standard |
|---|---|---|---|
| `bq` CLI | Whatever ships in current Google Cloud SDK | Run SQL fixes against BigQuery | Already the canonical analyzer transport per PROJECT.md; no alternative considered |
| `CURRENT_DATE("America/Phoenix")` | BigQuery standard SQL | Phoenix-aware date math in `sql/02`, `sql/03`, `sql/04` | Verified in Google Cloud docs as the exact signature for IANA timezone arguments |
| `LEAST(subquery, subquery)` | BigQuery standard SQL | Latest-common-snapshot across two joined tables | Already used in `sql/01`; D-05 extends to the actually-joined tables in `sql/02`, `sql/03` |
| `DATE_DIFF(CURRENT_DATE("America/Phoenix"), DATE(...), DAY)` | BigQuery standard SQL | Compute `days_since_published` and `days_stale` in Phoenix time | Verified pattern; the timezone-aware `CURRENT_DATE` is a valid first argument to `DATE_DIFF` |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `CHANGELOG.md` | — | Audit trail for each SQL fix + any rule-enforcement addition | Per `docs/maintenance.md` § "Evolving a business rule"; one line per material edit |
| Phase 1's recipe (`.claude/commands/run-analyzer.md`) | Phase 1 output | The file Phase 2 edits in place | Phase 2 never forks the recipe |
| Phase 1's `write-notion-report` Skill | Phase 1 output | Final publish step, unchanged in Phase 2 | Phase 2 only changes what's in the dictionary the Skill receives |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Markdown self-audit checklist | Separate `/voice-check` Skill | Adds a Skill surface that does what a checklist already does; rejected in D-02 |
| Inline parenthetical confidence | Notion callout block | Reserved for stale-data flags per D-07b; conflating signals would weaken both |
| `BUSINESS_RULES.md §N` references | Section-title references | CONCERNS.md flagged section-numbering drift across the repo; titles survive renumbering |
| External grep CI step | None | Deferred; self-audit is enough until reports drift in practice |
| Templated `MIN_VIDEO_AGE_DAYS` env var | Hardcoded `>= 14` literal | Deferred to v2; the literal lives in `CLAUDE.md` and `sql/03` and is not under tension yet |

**Installation:**

No installs. Phase 2 ships zero new dependencies; this complies with PROJECT.md's "no new Python deps" rule.

**Version verification:** Not applicable — Phase 2 introduces no packages.

## Package Legitimacy Audit

Not applicable. Phase 2 installs no external packages. No registry verification or slopcheck pass required.

## Architecture Patterns

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Operator triggers /run-analyzer (Phase 1's slash command, extended)     │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                  ┌──────────────────▼──────────────────┐
                  │ Step 1 (Phase 1): Data Health Check │
                  │ Runs sql/04, parses results,        │
                  │ identifies stale tables             │
                  └──────────────────┬──────────────────┘
                                     │
                  ┌──────────────────▼──────────────────────────────┐
                  │ Step 2 (Phase 1): Pull canonical SQL            │
                  │ Runs sql/02, sql/03 (now fixed under D-05)      │
                  │ Writes runs/{date}/queries/*.json               │
                  └──────────────────┬──────────────────────────────┘
                                     │
                  ┌──────────────────▼─────────────────────────────────┐
                  │ Step 3 (NEW in Phase 2): Read prior reports        │
                  │ Lexicographic top-3 from reports/*.md              │
                  │ Records 3 dates in summary.json.prior_reports_     │
                  │ consulted (D-10)                                   │
                  └──────────────────┬─────────────────────────────────┘
                                     │
                  ┌──────────────────▼─────────────────────────────────┐
                  │ Step 4 (REWORKED in Phase 2): Draft report         │
                  │ - Apply age-control rule (CLAUDE.md § "Age...")    │
                  │ - Apply hedging rule (CLAUDE.md § "Small samples") │
                  │ - Apply six-section structure (D-11 disclaimers)   │
                  │ - Stale-table disclaimers in dependent sections    │
                  │   (D-12)                                           │
                  │ - Inline (label, n=N) parentheticals per claim     │
                  │   (D-07); table claims add Confidence + n cols     │
                  └──────────────────┬─────────────────────────────────┘
                                     │
                  ┌──────────────────▼─────────────────────────────────┐
                  │ Step 5 (NEW in Phase 2): Self-audit                │
                  │ Walks the draft against the checklist:             │
                  │  - em dash (U+2014) + en dash (U+2013) scan        │
                  │  - banned-vocab scan (CLAUDE.md § Voice list)      │
                  │  - formulaic opener/closer scan                    │
                  │  - every pattern claim has (label, n=N)            │
                  │  - no <14-day video in top performers              │
                  │  - all 6 sections present in order                 │
                  │  - dependent sections disclaim stale tables        │
                  │ Fixes violations inline; records to summary.json   │
                  │ voice_audit: {checks_passed, fixes_applied}        │
                  └──────────────────┬─────────────────────────────────┘
                                     │
                  ┌──────────────────▼─────────────────────────────────┐
                  │ Step 6 (Phase 1): Invoke write-notion-report Skill │
                  │ Skill writes Notion blocks, returns page URL       │
                  └──────────────────┬─────────────────────────────────┘
                                     │
                  ┌──────────────────▼─────────────────────────────────┐
                  │ Step 7 (Phase 1): Persist                          │
                  │ reports/{date}.md + summary.json                   │
                  └────────────────────────────────────────────────────┘
```

Phase 2 inserts steps 3 and 5, reworks step 4, and extends the JSON written by step 7. Steps 1, 2, 6 are Phase 1's responsibility and don't change.

### Recommended Project Structure

No new files. Phase 2 edits in place:
```
.claude/commands/run-analyzer.md   # EDITED — three new sections, one expanded section
sql/02_top_full_length_videos.sql   # EDITED — Phoenix tz + LEAST snapshot + no LIMIT
sql/03_age_controlled_performance.sql  # EDITED — Phoenix tz + LEAST snapshot + no LIMIT
sql/04_data_health_check.sql        # EDITED — Phoenix tz only
runs/README.md                      # EDITED — document new summary.json fields
CHANGELOG.md                        # APPENDED — one entry per SQL fix + one for rule enforcement
```

### Pattern 1: BigQuery Phoenix-time date math
**What:** Use `CURRENT_DATE("America/Phoenix")` as the first argument to `DATE_DIFF` so date-boundary edge cases align with the upstream `youtube-bigquery-pipeline` scheduler (which runs in Phoenix).
**When to use:** Every place the existing SQL files use bare `CURRENT_DATE()`.
**Example:**
```sql
-- Source: Google Cloud BigQuery date_functions docs [CITED: docs.cloud.google.com/bigquery/docs/reference/standard-sql/date_functions]
DATE_DIFF(CURRENT_DATE("America/Phoenix"), DATE(m.published_at), DAY) AS days_since_published
```

### Pattern 2: Latest-common-snapshot across two joined tables (D-05)
**What:** Compute `latest_common = LEAST(MAX(snapshot_date)_table_a, MAX(snapshot_date)_table_b)` and filter both join sides to that date. Prevents silent row drops when the upstream pipeline lands the two tables out of sync.
**When to use:** Any query joining `video_metadata` and `daily_video_stats` (or any two snapshot tables).
**Example (for `sql/02` and `sql/03`):**
```sql
-- Source: pattern borrowed from sql/01_latest_snapshot_overview.sql, extended to the joined tables
WITH latest_common AS (
    SELECT LEAST(
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.video_metadata`),
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.daily_video_stats`)
    ) AS snapshot_date
)
SELECT
    m.title,
    m.video_type,
    m.duration_formatted,
    m.published_at,
    DATE_DIFF(CURRENT_DATE("America/Phoenix"), DATE(m.published_at), DAY) AS days_since_published,
    s.view_count,
    s.like_count,
    s.comment_count
FROM `youtube_analytics.video_metadata` m
JOIN `youtube_analytics.daily_video_stats` s
    USING (video_id, snapshot_date)
WHERE m.snapshot_date = (SELECT snapshot_date FROM latest_common)
    AND m.video_type = 'full_length'
ORDER BY s.view_count DESC;
-- LIMIT removed per D-05; dataset is small and age-filter narrows the set in sql/03
```

### Pattern 3 (reference only; deferred per D-06): Four-table `LEAST` extension
**What:** When future work needs a snapshot common to all four analytics tables.
**Example (DO NOT implement in Phase 2; document for Phase 3):**
```sql
-- Source: extension of sql/01 pattern; NOT implemented in Phase 2 (deferred per D-06)
-- ⚠ CAVEAT: BigQuery's LEAST returns NULL if any argument is NULL.
-- If daily_video_analytics or daily_traffic_sources is empty, the whole result is NULL.
-- A four-table variant should null-coalesce or branch on the staleness signal from sql/04.
WITH latest_common AS (
    SELECT LEAST(
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.video_metadata`),
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.daily_video_stats`),
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.daily_video_analytics`),
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.daily_traffic_sources`)
    ) AS snapshot_date
)
SELECT ...
```
NULL-on-any-NULL behavior verified [CITED: justrocketscience.com/post/bigquery_least_nulls; datawise.dev/greatest-least-in-bigquery]. Two-table `sql/01` works today because both source tables have data; a four-table variant must handle the empty-table case before shipping.

### Pattern 4: Eligible-count query for confidence labels (ANALYSIS-03)
**What:** Query the live `video_metadata` table for the count of *eligible* full-length videos (passing the 14-day filter), at the latest common snapshot. This `N` is what goes into the `(label, n=N)` parenthetical.
**When to use:** Once per run, at the start of the draft step. Cache the result; every confidence label uses the same `N` unless a claim is scoped to a sub-population (in which case scope the count).
**Example:**
```sql
-- Source: derived from sql/02 + sql/03 patterns
WITH latest_common AS (
    SELECT LEAST(
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.video_metadata`),
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.daily_video_stats`)
    ) AS snapshot_date
)
SELECT
    COUNT(*) AS eligible_count,
    (SELECT COUNT(*) FROM `youtube_analytics.video_metadata` m2
        WHERE m2.snapshot_date = (SELECT snapshot_date FROM latest_common)
          AND m2.video_type = 'full_length') AS total_full_length
FROM `youtube_analytics.video_metadata` m
WHERE m.snapshot_date = (SELECT snapshot_date FROM latest_common)
    AND m.video_type = 'full_length'
    AND DATE_DIFF(CURRENT_DATE("America/Phoenix"), DATE(m.published_at), DAY) >= 14;
```
Planner option: roll `eligible_count` directly into the data-health summary so no new SQL file is needed; or add `sql/05_eligible_video_count.sql` per the numeric-prefix convention. Default: roll into the recipe step using inline `bq query`, avoiding a new file.

### Pattern 5: Inline parenthetical confidence (D-07)
**What:** Every prose pattern claim ends with ` (label, n=N).` where label is one of `low confidence` / `moderate confidence` / `standard confidence`. Banned: dash-clauses (would violate D-07's no-em-dash rule and the global "no em dash" rule).
**Example:**
```markdown
VID042 "GraphQL vs REST" pulled 4,300 views in its first 30 days,
about 5× the channel median of 860 (standard confidence, n=18).
```
For table-shaped findings:
```markdown
| Video | Views (first 30d) | vs. median | Confidence | n |
|-------|-------------------|------------|------------|---|
| GraphQL vs REST | 4,300 | 5× | standard | 18 |
```

### Anti-Patterns to Avoid
- **Hardcoding the video count.** `CLAUDE.md` says "Query the current count from `video_metadata` (latest snapshot) at the start of every run. Do not hardcode it." Phase 2 must pull `eligible_count` each run.
- **Using em dashes anywhere in the report.** Both U+2014 (em dash) and U+2013 (en dash) are banned per `CLAUDE.md` § Voice. The self-audit must scan for both.
- **Citing prior reports in prose.** `"As we noted last week, ..."` is banned by D-08. `"For the third consecutive week, X has held"` is allowed if self-contained per D-09.
- **Silently skipping a section that has no findings.** D-11: heading always renders; body explicitly says what's missing.
- **Computing against a stale table.** D-12: dependent sections must disclaim the staleness, never produce a number from stale data.
- **Section-number references like `BUSINESS_RULES.md §3`.** Use the section title. CONCERNS.md flagged this as fragility-multiplier debt; Phase 2 must not add to it.
- **Bypassing `write-notion-report` and calling Notion MCP directly.** `CLAUDE.md`: "Do not try to call Notion directly."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "Latest common snapshot" join | Hand-tracked snapshot logic in each query | The `LEAST(subquery, subquery)` CTE pattern from `sql/01` | Already proven and the only correct way to avoid silent row drops |
| Phoenix-time conversion | Manual `DATE_SUB(CURRENT_DATE, INTERVAL 7 HOUR)` math | `CURRENT_DATE("America/Phoenix")` | Direct IANA-tz support is BigQuery-native and handles DST correctly (Arizona doesn't observe DST, but the function still does the right thing) |
| Markdown→Notion translation | Custom block-builder in the analyzer | Phase 1's `write-notion-report` Skill (which can use Notion API `markdown` param per `POST /v1/pages`) | Phase 1 owns this; Phase 2 only changes the dict it receives |
| Voice / vocabulary linter | A grep script or external tool | The self-audit step in the recipe | D-01 + D-02; matches PROJECT.md's "no application framework" rule |
| Confidence threshold logic | A computed expression | The thresholds in `CLAUDE.md` § "Small samples get hedged" applied by the analyzer | `CLAUDE.md` is the source of truth; duplicating in code creates drift risk |
| Prior-report parsing | A regex pipeline | Direct file read + Claude's natural prose comprehension | Three ~2-3KB files; the analyzer reads them as prose |

**Key insight:** Phase 2's correctness comes from removing ambiguity in the analyst's instructions, not from adding executable enforcement. Every Phase 2 "rule" is something Claude already knows how to do; Phase 2 just makes the recipe step explicit enough that it actually happens every run.

## Runtime State Inventory

Not applicable. Phase 2 is a greenfield extension of Phase 1's recipe (no rename, no refactor, no migration). The closest thing to "runtime state" is the existing `reports/` archive that Phase 2 reads — but that's a designed read, not state-discovery work.

## Common Pitfalls

### Pitfall 1: SQL file changes silently produce different numbers without a CHANGELOG entry
**What goes wrong:** The three D-05 SQL fixes will materially change the numbers `sql/02` and `sql/03` return on any day where the two source tables have different latest snapshots. If the change ships without a `CHANGELOG.md` entry, a future Kyle (or viewer) auditing past reports won't know why the comparison shifted.
**Why it happens:** SQL edits feel mechanical; the convention to log them is documented in `docs/maintenance.md` but not enforced by tooling.
**How to avoid:** Each of the three SQL files gets its own CHANGELOG bullet under one dated H2 heading. The entry names the bug fixed and the before/after behavior in one line each. Per `docs/maintenance.md` § "Evolving a business rule".
**Warning signs:** A SQL diff that doesn't have an accompanying `CHANGELOG.md` diff in the same commit.

### Pitfall 2: The "n" in `(label, n=N)` drifts away from the actual comparison set
**What goes wrong:** `N` is supposed to be the count of *eligible* videos in the comparison set per D-07 — i.e., videos passing the 14-day filter that the specific claim is drawn from. A naïve implementation will use the total `video_count_full_length` (which Phase 1's `summary.json` already records), inflating `N` and silently weakening the hedging.
**Why it happens:** It's easier to grab `summary.json.video_count_full_length` than to derive eligibility per claim.
**How to avoid:** The recipe step computes `eligible_count` once (Pattern 4 above) and uses it for any claim drawn from the full eligible set. For sub-population claims (e.g., "only tutorials"), the analyzer must scope the count to that sub-population. Self-audit checklist item: "every confidence label cites a count that reflects the comparison set the claim actually drew from."
**Warning signs:** A claim about a tutorial sub-segment carrying `n=18` (the channel-wide eligible count) instead of, say, `n=7` (tutorials only).

### Pitfall 3: Self-audit step skips when context is tight
**What goes wrong:** The analyzer drafts, runs out of patience (or context), and writes a "done" without working through the checklist. The published report is structurally fine but quietly violates one or more voice rules.
**Why it happens:** Checklist enforcement is not load-bearing in any executable sense; it's prose.
**How to avoid:** Per Anthropic's Skill best practices, express the checklist as a copy-into-response checkbox list with explicit "tick each before proceeding" framing [CITED: platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices]. Record `voice_audit.checks_passed` to `summary.json` so a missing entry is visible after the fact.
**Warning signs:** `summary.json.voice_audit` missing or partial; banned vocab or em dash present in a published report.

### Pitfall 4: Cross-week framing slides into "as we said last week"
**What goes wrong:** D-09 allows self-contained multi-week framing; D-08 forbids citing prior reports. The line is easy to cross by accident: `"This continues the trend we observed..."` is a banned reference; `"For the third consecutive week..."` is allowed.
**Why it happens:** Natural prose flows toward reference; the analyzer has the prior reports in working memory.
**How to avoid:** Self-audit checklist item: "every multi-week claim stands on its own without requiring the reader to have seen a prior report." If the reader couldn't follow the sentence as a standalone, rewrite.
**Warning signs:** Phrases like "as noted", "as we said", "last week's report", "the prior report".

### Pitfall 5: Stale-table disclaimer pile-up
**What goes wrong:** With two of four tables 89 days stale at planning time, three of the six sections may each carry "couldn't compute X because Y is stale" disclaimers. Read as a pile, this reads as 60% disclaimer and 40% analysis, which doesn't help anyone.
**Why it happens:** D-12 says dependent sections must name the staleness; left literal, every dependent claim becomes its own disclaimer.
**How to avoid:** When multiple findings in the same section would all disclaim the same stale table, collapse to one disclaimer per section: `"Watch-time and traffic-source analysis is unavailable: daily_video_analytics is 89 days stale (see Data Health)."` Then list whatever non-stale-dependent findings are present, if any. Phase 2 recipe step should make this collapse explicit.
**Warning signs:** A "Patterns worth watching" section with four bullets, three of which start identically.

### Pitfall 6: BigQuery `LEAST(NULL, ...)` returns NULL
**What goes wrong:** If a four-table `LEAST` extension is added later (deferred per D-06) and any one source table is genuinely empty, the whole `latest_common` resolves to NULL and the downstream WHERE clause filters everything out. Reports go quiet without an error.
**Why it happens:** BigQuery's `LEAST` propagates NULLs; there's no `IGNORE NULLS` option [CITED: justrocketscience.com/post/bigquery_least_nulls].
**How to avoid:** Not a Phase 2 issue (two-table `LEAST` is safe because both source tables have data per Phase 1's data-health check). When Phase 3 / v2 extends to four tables, branch on the data-health signal first, or use `COALESCE(MAX(snapshot_date), DATE '1900-01-01')` to push empty tables out of the running. Documented in Pattern 3 caveat above.
**Warning signs:** Two-table version doesn't have this risk; flag it only when extension is considered.

## Code Examples

### Phase 2 SQL fix: `sql/02_top_full_length_videos.sql` (D-05, after)
```sql
-- ─── Top full-length videos by views (latest snapshot) ───────
-- The analyzer's "what's working" foundation.
-- Filters out shorts. Ranks full-length videos by cumulative views with engagement.
-- Apply the age-control rule (CLAUDE.md § "Age control is non-negotiable") downstream — this is raw data.
--
-- Dataset name: bare `youtube_analytics.<table>` form; bq CLI resolves project from
-- your gcloud config. Replace `youtube_analytics` if your dataset has a different name.
--
-- Timezone: CURRENT_DATE("America/Phoenix") aligns date math with the upstream
-- youtube-bigquery-pipeline scheduler. See BUSINESS_RULES.md § "Data health expectations".
--
-- Latest-common-snapshot logic: takes MIN(MAX(snapshot_date)) across video_metadata
-- and daily_video_stats so we never join a metadata row at a date where stats
-- haven't arrived yet (which would silently drop rows).

WITH latest_common AS (
    SELECT LEAST(
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.video_metadata`),
        (SELECT MAX(snapshot_date) FROM `youtube_analytics.daily_video_stats`)
    ) AS snapshot_date
)
SELECT
    m.title,
    m.video_type,
    m.duration_formatted,
    m.published_at,
    DATE_DIFF(CURRENT_DATE("America/Phoenix"), DATE(m.published_at), DAY) AS days_since_published,
    s.view_count,
    s.like_count,
    s.comment_count
FROM `youtube_analytics.video_metadata` m
JOIN `youtube_analytics.daily_video_stats` s
    USING (video_id, snapshot_date)
WHERE m.snapshot_date = (SELECT snapshot_date FROM latest_common)
    AND m.video_type = 'full_length'
ORDER BY s.view_count DESC;
```
Notes: removed `LIMIT 20` per D-05; replaced `BUSINESS_RULES.md §3` reference with section-title reference to `CLAUDE.md`; expanded header comment to document the new latest-common-snapshot logic; updated header note about `BUSINESS_RULES.md` to reference by section title.

### Phase 2 SQL fix: `sql/03_age_controlled_performance.sql` (D-05, after — same pattern)
Apply the same three changes:
1. Add `latest_common` CTE with `LEAST(...)`.
2. Replace `WHERE m.snapshot_date = (SELECT MAX(snapshot_date) FROM video_metadata)` with `WHERE m.snapshot_date = (SELECT snapshot_date FROM latest_common)`.
3. Replace `CURRENT_DATE()` with `CURRENT_DATE("America/Phoenix")` in both the WHERE clause and the SELECT-list `DATE_DIFF`.
4. Remove `LIMIT 20`.
5. Update header comment: reference `CLAUDE.md § "Age control is non-negotiable"` and `BUSINESS_RULES.md § "Data health expectations"` by section title, not number.

### Phase 2 SQL fix: `sql/04_data_health_check.sql` (D-05, after)
Single change in four places: `CURRENT_DATE()` → `CURRENT_DATE("America/Phoenix")` in each `DATE_DIFF` call. Update header comment to remove the conditional "if your scheduling timezone differs" language and instead state Phoenix as the canonical timezone per `BUSINESS_RULES.md § "Data health expectations"`. Replace the broken `BUSINESS_RULES.md §5` reference (§5 doesn't exist; CONCERNS.md flagged this) with the section-title form.

### Self-audit checklist (the new recipe step, expressed as runnable markdown)
```markdown
## Step: Self-audit (run AFTER draft is assembled, BEFORE invoking write-notion-report)

Copy this checklist into your scratch space and tick each item:

```
Self-audit progress:
- [ ] Six sections present in order: Data Health, Headline, What is working, What is not working, Patterns worth watching, Open questions
- [ ] Every section heading renders (sections with no findings carry an explicit "Nothing material to report this week." or stale-table disclaimer)
- [ ] No video with days_since_published < 14 appears in "What is working" top-performer claims
- [ ] Cross-age comparisons use first-30-day window OR are explicitly labeled as a views-per-day proxy
- [ ] Every pattern claim ends with (label, n=N) parenthetical OR appears in a table with Confidence + n columns
- [ ] Each "n" cited matches the comparison set the claim actually drew from
- [ ] No em dashes (U+2014) anywhere in the draft
- [ ] No en dashes (U+2013) used as punctuation
- [ ] None of the banned vocabulary list from CLAUDE.md § Voice appears: leverage, robust, seamless, navigate, delve, transformative, elevated, etc. (full list is in CLAUDE.md § "Voice")
- [ ] No formulaic openers ("Great news!", "Overall,", "In conclusion,", contrastive "Not X, Y" reframes)
- [ ] No prior-report citation in prose ("as we said last week", "the prior report", "as noted")
- [ ] Multi-week claims (if any) stand on their own without requiring reader to have seen prior reports
- [ ] Stale-table downstream impact disclaimed in every dependent section (one collapsed disclaimer per section preferred)
- [ ] Numbers cited are present in the underlying runs/{date}/queries/*.json (spot-check 3 random claims)
```

For each failed check: fix the violation inline in the draft. Record the fix as an entry in summary.json.voice_audit.fixes_applied with section and one-line description.

For each passed check: record as an entry in summary.json.voice_audit.checks_passed.

When all checks pass, proceed to invoke write-notion-report.
```
Pattern source: copy-into-response checklist with explicit per-item ticking, per Anthropic Skill best practices [CITED: platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices].

### Prior-report read step (the other new recipe step)
```markdown
## Step: Read prior reports for calibration (run BEFORE draft step)

1. List existing reports sorted lexicographically (YYYY-MM-DD names sort correctly):
   `ls reports/ | grep -E '^\d{4}-\d{2}-\d{2}.*\.md$' | sort | tail -n 3`
2. Read those three files in full. Hold their content in working memory.
3. Use them to:
   - Upgrade confidence labels if a pattern has held across runs and the eligible set has grown
   - Downgrade confidence if a pattern has weakened or the sample shrank
   - Avoid restating findings verbatim (fresh-frame, don't copy)
   - Notice regressions: was a video a top performer two reports ago and isn't now?
4. Do NOT cite the prior reports in the new report's prose. The standalone-tone rule in CLAUDE.md ("assume Kyle has not seen the previous week's report") holds.
5. Record the dates consulted in summary.json.prior_reports_consulted as a list of YYYY-MM-DD strings.

If fewer than 3 prior reports exist: read what's there (zero, one, or two); do not block; record the actual list (which may be empty) in summary.json.

Cross-week patterns may surface in "Patterns worth watching" when the framing is self-contained
(e.g., "For the third consecutive week, X..."). Citation of prior reports ("as we said last week, X")
is forbidden.
```

### Extended `summary.json` schema (D-10 + voice_audit)
```json
{
  "run_date": "2026-05-25",
  "run_started_at": "2026-05-25T09:00:00-07:00",
  "...": "all Phase 1 fields unchanged",
  "prior_reports_consulted": ["2026-05-18", "2026-05-11", "2026-05-04"],
  "voice_audit": {
    "checks_passed": [
      "six_sections_in_order",
      "age_control_enforced",
      "confidence_labels_present",
      "no_em_dashes",
      "no_banned_vocab",
      "no_formulaic_openers",
      "no_prior_report_citation",
      "stale_table_disclaimers_present"
    ],
    "fixes_applied": [
      {"section": "Patterns", "fix": "Replaced em dash with comma in framing of tool-tutorials trend"},
      {"section": "What is working", "fix": "Added (standard confidence, n=18) to median-views claim"}
    ]
  }
}
```
Planner: if Phase 1 has already shipped a `summary.json` writer, this is an additive change. If Phase 1's writer enforces a closed schema, Phase 2 must add these fields to the writer's allowed-keys list.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `CURRENT_DATE()` (UTC default) for Phoenix-time math | `CURRENT_DATE("America/Phoenix")` | Always available in BigQuery standard SQL; just unused | Phoenix–UTC edge cases at day boundaries disappear |
| `MAX(snapshot_date) FROM video_metadata` as the join filter | `LEAST(MAX(...)_a, MAX(...)_b)` CTE | Pattern already in `sql/01`; just unused in `sql/02`, `sql/03` | Silent row drops on cross-table staleness are eliminated |
| Hand-rolled markdown→Notion translation | Notion API `POST /v1/pages` with `markdown` body param | Released by Notion; usable via MCP create-pages [CITED: developers.notion.com/guides/data-apis/working-with-markdown-content] | Phase 1's Skill should use this; markdown tables map to native Notion tables; Phase 2 needs no special Skill behavior |
| External linter / CI grep for voice | Self-audit step in the recipe | D-01 + Anthropic Skill best-practices copy-into-checklist pattern | Single source of truth; no second-system to maintain |

**Deprecated/outdated:**
- The `BUSINESS_RULES.md §3` reference in `sql/02:4` and `sql/03:2,10` is wrong (§3 is data health; age control lives in `CLAUDE.md`). Phase 2's SQL header comments use section titles instead.
- The `BUSINESS_RULES.md §5` reference in `sql/04:2` doesn't resolve (§5 doesn't exist). Phase 2 uses section title.
- `LIMIT 20` in `sql/02` and `sql/03` was a guard against thousands of rows; the dataset is ~24 videos with eligibility further narrowing it. Phase 2 removes per D-05.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 1 ships `/run-analyzer` as a linear recipe with a clean "draft → publish" seam (per `01-CONTEXT.md` D-02 / D-04) | Architecture Patterns | If Phase 1's recipe wires draft → publish tightly, Phase 2 must refactor that seam first; D-04 already calls this out as planner work |
| A2 | Phase 1's Skill input contract uses a structured dict with per-finding records (per `01-CONTEXT.md` Claude's Discretion, defaulted) | Architecture Patterns | If Phase 1 instead ships a single `markdown_body` string with no per-finding shape, the structured `confidence: {label, n}` field has nowhere to live and confidence becomes a prose-only signal. Lower fidelity but not blocking. |
| A3 | Phase 1's `summary.json` writer is additive-friendly (per `runs/README.md` schema as documentation, not closed schema) | Extended summary.json schema | If Phase 1 enforces a closed schema, Phase 2 must add `prior_reports_consulted` and `voice_audit` to its allowed-keys list explicitly |
| A4 | Eligible-count query can be inlined in the recipe step via `bq query`, avoiding a new `sql/05_eligible_count.sql` file | Pattern 4 | If maintenance prefers SQL files, planner can promote it; either is fine |
| A5 | The `markdown` parameter to Notion API `POST /v1/pages` preserves plain-text parentheticals like `(moderate confidence, n=7)` without auto-formatting | Notion rendering | Documentation didn't explicitly confirm inline parenthetical behavior (search result said the docs don't address this). LOW confidence; first real run will confirm. If Notion mangles the parenthetical (e.g., turning `n=7` into a bold node), Phase 2 may need to ask Phase 1's Skill to use the `children` parameter with explicit `paragraph` blocks instead of the `markdown` body |
| A6 | The 14-day eligibility threshold is the right boundary (`<5` = low / `5–10` = moderate / `≥10` = standard) — `5` is the LOW boundary | Pattern 4 + self-audit | Re-read of `CLAUDE.md` § "Small samples get hedged": "Fewer than 5 videos behind a pattern: low confidence (small sample). 5 to 10 videos: moderate confidence. 10 or more: standard confidence." So `n=4`→low, `n=5`→moderate, `n=10`→standard. Verified. |
| A7 | Lexicographic sort of `reports/*.md` files yields chronological order | Prior-report read step | TRUE because the naming convention is `YYYY-MM-DD.md`, and ISO-8601 dates sort lexicographically in chronological order. Same-day retries `YYYY-MM-DD-2.md` sort *after* `YYYY-MM-DD.md` which is desired behavior. |
| A8 | The banned-vocabulary list lives in `CLAUDE.md` § Voice (project-specific) and is the authoritative one for the self-audit (global `~/.claude/CLAUDE.md` Prose & Anti-AI-Voice list is reference, not enforcement) | Self-audit checklist | Confirmed by CONTEXT.md "specifics" section. Self-audit references project `CLAUDE.md` only. |
| A9 | Three prior reports × ~2–3KB each = ~10KB of additional context per run, well within budget | Prior-report read step | TRUE at current report sizes. If reports grow to ~20KB each (longer than the design point), the planner may want to extract a "calibration summary" from prior reports rather than read them in full. Not a Phase 2 concern. |
| A10 | The `markdown` body param to Notion `POST /v1/pages` is mutually exclusive with `children` (per Notion API docs) | Phase 1 Skill integration | Phase 2 doesn't touch the Skill, so this matters only if A5 turns out to be a problem and the Skill needs to switch to `children`-shaped blocks. Documented for completeness. |

**A2, A3, A5 are the assumptions to flag in the plan as "verify against Phase 1's actual implementation."** The other items are confirmed.

## Open Questions

1. **Does Notion's `markdown` body param preserve inline parentheticals cleanly?**
   - What we know: The `markdown` param exists, markdown tables map to native Notion tables, the doc explicitly covers block-level handling [CITED: developers.notion.com/guides/data-apis/working-with-markdown-content].
   - What's unclear: Whether `(moderate confidence, n=7)` survives without being auto-formatted (italicized, bolded, or stripped). The Notion API doc doesn't address inline behavior.
   - Recommendation: Phase 2's first real run is the test. If parentheticals mangle, escalate to Phase 1's Skill owner to switch to the `children` parameter (explicit `paragraph` block with `rich_text` array of plain-text segments).

2. **Is Phase 1's recipe extension point clean enough for the three insertions?**
   - What we know: `01-CONTEXT.md` D-02 says ~80–150 lines of linear markdown; D-04 says "self-audit is a recipe step, not a Skill invocation."
   - What's unclear: Whether Phase 1's draft step is monolithic or already broken into sub-steps the planner can insert between. Depends on Phase 1's final shape.
   - Recommendation: Plan the three new steps assuming a clean seam; flag the refactor as a fallback contingency in the plan.

3. **Should `eligible_count` be its own SQL file (`sql/05_*.sql`) or stay inline in the recipe?**
   - What we know: The numeric-prefix convention from `docs/maintenance.md` welcomes new files; an inline `bq query` works too.
   - What's unclear: Which the planner / Kyle prefers for navigability vs. file count.
   - Recommendation: Default to inline (simpler, no new file, no new CHANGELOG entry beyond the rule-enforcement one). Planner may promote it to `sql/05_eligible_video_count.sql` if the recipe gets crowded.

4. **Do same-day retries (`YYYY-MM-DD-2.md`) count toward the 3-most-recent prior-report read?**
   - What we know: Lexicographic sort would place `2026-05-24-2.md` after `2026-05-24.md` and before `2026-05-25.md`.
   - What's unclear: Whether a retry of today's run "counts" as a prior report or as the current run-in-progress.
   - Recommendation: Filter out files whose date prefix matches the current run date before taking the top 3. The retry is part of "this run", not the calibration archive. Self-audit checklist item: "prior_reports_consulted does not include today's run".

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `bq` CLI | D-05 SQL fix verification | ✓ (Phase 1 prereq; CONTEXT.md confirms BigQuery connectivity already verified) | Whatever ships with current gcloud SDK | None — Phase 2 inherits Phase 1's transport choice |
| `youtube_analytics.video_metadata` | Eligible-count query | ✓ (fresh as of 2026-05-25 per CONTEXT.md) | Latest snapshot | If stale: data-health check stops the run before Phase 2's steps fire |
| `youtube_analytics.daily_video_stats` | `sql/02`, `sql/03` LEAST CTE | ✓ (fresh) | Latest snapshot | Same as above |
| `youtube_analytics.daily_video_analytics` | Some "Patterns" findings | ✗ (89 days stale at planning) | 2026-02-25 snapshot | D-12: dependent section disclaims; no fallback computation |
| `youtube_analytics.daily_traffic_sources` | Some "Patterns" findings | ✗ (89 days stale at planning) | 2026-02-25 snapshot | Same |
| Phase 1's `/run-analyzer` recipe | Edit target for the three new steps | Phase 1 in flight | TBD | If Phase 1 lands materially different: replan Phase 2's recipe extension |
| Phase 1's `write-notion-report` Skill | Final publish step (unchanged in Phase 2) | Phase 1 in flight | TBD | Same |
| `CHANGELOG.md` | Required entries for D-05 SQL fixes | ✓ (exists in repo) | — | None — required by `docs/maintenance.md` |
| `reports/*.md` archive | Prior-report read | Empty at planning (`ls reports/` returned only `README.md` as of 2026-05-25) | — | Recipe must handle zero-prior-reports case gracefully; default to "no calibration data, all confidence labels derive from this run's eligible-count only" |

**Missing dependencies with no fallback:** None blocking Phase 2.

**Missing dependencies with fallback:**
- `daily_video_analytics` and `daily_traffic_sources` (stale) — Phase 2's D-12 disclaimer machinery handles this by design.
- Prior `reports/*.md` (none exist at planning) — Phase 2's first run will have zero prior reports; the recipe step must not block on fewer than 3 prior reports.

## Validation Architecture

> `.planning/config.json` doesn't exist; per the researcher guidance, treat `workflow.nyquist_validation` as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None — repo has no automated test suite (per `.planning/codebase/CONCERNS.md` § "Test Coverage Gaps") |
| Config file | None |
| Quick run command | `/run-analyzer` (the recipe is its own integration test; output verified by reading `reports/{date}.md`) |
| Full suite command | Same as quick — one-shot end-to-end run |
| Phase gate | Run the analyzer end-to-end against the live `youtube_analytics` dataset; visually verify all five ROADMAP.md Phase 2 success criteria are met in the resulting `reports/{date}.md`; confirm `summary.json.voice_audit.checks_passed` lists all expected checks |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANALYSIS-01 | No video with `days_since_published < 14` in "What is working" | manual (visual inspection of report + `runs/{date}/queries/`) | None | n/a |
| ANALYSIS-02 | Cross-age claims use first-30-day or explicitly labeled proxy | manual (read claim, verify label) | None | n/a |
| ANALYSIS-03 | Every pattern claim has `(label, n=N)`; `N` matches live eligible count | smoke (bq dry-run on the eligible-count query) + manual | `bq query --use_legacy_sql=false --dry_run "$(cat sql/03_...)"` | n/a |
| ANALYSIS-04 | Trending claims gated by `>=14` days of data | manual (same as ANALYSIS-01) | None | n/a |
| ANALYSIS-05 | 3 most recent `reports/*.md` read before drafting; `prior_reports_consulted` populated | structural (read `summary.json`) | `jq '.prior_reports_consulted' runs/{date}/summary.json` | n/a |
| REPORT-01 | Six sections in order, headings always present | structural (grep headings in report) | `grep -E '^## (Data Health\|Headline\|What is working\|What is not working\|Patterns worth watching\|Open questions)' reports/{date}.md` | n/a |
| REPORT-02 | Findings include numbers + age + confidence inline | manual | None | n/a |
| REPORT-03 | Voice rules pass (no em dash, no banned vocab, no formulaic openers) | structural (grep) | `grep -nE '—|–' reports/{date}.md && echo FAIL` ; `grep -niE '\b(leverage\|robust\|seamless\|delve\|navigate\|transformative\|elevated)\b' reports/{date}.md && echo FAIL` | n/a |

### Sampling Rate
- **Per SQL fix commit:** `bq query --dry_run` on the affected SQL file (validates BigQuery accepts the new `CURRENT_DATE("America/Phoenix")` + `LEAST` syntax).
- **Per recipe edit commit:** No automated test; the recipe is prose and won't be exercised until a full run.
- **Phase gate:** One real end-to-end `/run-analyzer` invocation against live BigQuery; visual review of `reports/{date}.md` against the five ROADMAP success criteria; structural check of `summary.json.voice_audit`.

### Wave 0 Gaps
*(No traditional test suite to build. The closest thing is a structural grep for voice violations, which CONTEXT.md's Claude's Discretion explicitly defers to v2. Wave 0 work for Phase 2 is the SQL fixes + recipe extensions, not new tests.)*

- [ ] No new test files needed. Phase 2 ships against the existing "end-to-end run = the test" model.
- [ ] *(Optional, deferred per CONTEXT.md):* `scripts/voice_check.sh` running grep against `reports/*.md` for em dashes + banned vocab. Not required for Phase 2.

## Security Domain

> `security_enforcement` defaults to enabled. Phase 2 surface area for security review is narrow.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 2 adds no new auth surface; inherits Phase 1's bq CLI auth |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | yes (low surface) | The eligible-count query takes no user input; the recipe step reads prior reports from a fixed path (`reports/`); no SQL injection vector |
| V6 Cryptography | no | n/a |
| V14 Configuration | yes | `CHANGELOG.md` entries for SQL changes are an integrity-of-config control already prescribed by `docs/maintenance.md` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via dataset templating | Tampering | Phase 2 doesn't add new templating; uses bare `youtube_analytics.<table>` form (BQ-01 in Phase 1 handles dataset substitution) |
| Prompt injection from video titles into the analyzer's reasoning | Tampering | CONCERNS.md flagged this; Phase 2 doesn't expand the attack surface but doesn't mitigate it either. Mitigation is Phase 1's BQ guardrail ("only SELECT, refuse DDL/DML") plus least-privilege bq auth |
| Confidence label fabrication (analyzer hallucinates `n=N` without querying) | Tampering of analytical output | The eligible-count query is a real `bq` call whose result lands in `runs/{date}/queries/`. Audit trail is the mitigation |
| Voice-audit lies (analyzer claims it ran the checklist when it didn't) | Tampering of audit metadata | `summary.json.voice_audit.fixes_applied` is auditable; if `checks_passed` lists every check but the report has em dashes, the discrepancy is visible after the fact. Deferred-CI-grep idea is the v2 mitigation |
| Stale-data silent fallback | Information disclosure (publishing a number that's 89 days old as if fresh) | D-12 disclaimer rule; data-health check + per-section disclaimer is the mitigation |

## Sources

### Primary (HIGH confidence)
- BigQuery date functions docs — `CURRENT_DATE(timezone_string)` signature, `DATE_DIFF` first-argument compatibility, IANA timezone string support: [docs.cloud.google.com/bigquery/docs/reference/standard-sql/date_functions](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/date_functions)
- Anthropic Skill authoring best practices — copy-into-response checklist pattern, validation-loop pattern, content-review pattern: [platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- Notion API working-with-markdown-content guide — `POST /v1/pages` with `markdown` body param, block-type mapping table, mutual exclusion with `children`: [developers.notion.com/guides/data-apis/working-with-markdown-content](https://developers.notion.com/guides/data-apis/working-with-markdown-content)
- `CLAUDE.md` (project) — voice, age-control, hedging thresholds, six-section structure, prior-report rule
- `BUSINESS_RULES.md` (project) — Phoenix timezone, table grain, join keys
- `sql/01_latest_snapshot_overview.sql` — source of the `LEAST(...)` CTE pattern Phase 2 borrows
- `.planning/codebase/CONCERNS.md` — names the three SQL bugs Phase 2 fixes; flags section-numbering drift
- `.planning/codebase/CONVENTIONS.md` — SQL formatting, snake_case derived columns, `_proxy` suffix convention

### Secondary (MEDIUM confidence)
- BigQuery `LEAST` NULL-handling behavior: [justrocketscience.com/post/bigquery_least_nulls](https://justrocketscience.com/post/bigquery_least_nulls), [datawise.dev/greatest-least-in-bigquery](https://datawise.dev/greatest-least-in-bigquery) — Confirms `LEAST(NULL, x)` returns NULL; relevant only for the deferred four-table extension (Pattern 3 caveat)
- General BigQuery `CURRENT_DATE` with timezone usage examples: [medium.com — Time zone conversions in BigQuery](https://medium.com/@adarsh.namdev89/time-zone-conversions-in-bigquery-ea70afb12be8)

### Tertiary (LOW confidence)
- Inline parenthetical preservation in Notion `markdown` API body (A5): no authoritative source found — Notion's markdown guide covers block types but not inline text edge cases. Flagged as Open Question 1; first real Phase 2 run is the verification.

## Metadata

**Confidence breakdown:**
- SQL fix patterns (D-05): HIGH — BigQuery `CURRENT_DATE` timezone signature confirmed in official docs; `LEAST` two-table pattern is already proven in `sql/01`; `LIMIT` removal is policy, not technical
- Self-audit recipe extension (D-01): HIGH — copy-into-response checklist pattern is explicitly documented as a Skill best practice
- Prior-report calibration (D-08, ANALYSIS-05): HIGH — lexicographic sort works because of ISO-8601 naming; analyzer already understands "use for context, don't cite" framing from CLAUDE.md
- Confidence label derivation (D-07): HIGH — thresholds are explicit in `CLAUDE.md`; eligible-count query is a small extension of existing SQL patterns
- Notion rendering of inline parentheticals (A5): LOW — first real run is the test; fallback path (Skill switches to `children` blocks) is known
- Phase 1 recipe extension seam (A1): MEDIUM — depends on Phase 1's final shape; D-04 already calls out the refactor contingency

**Research date:** 2026-05-25
**Valid until:** 2026-06-24 (30 days; the BigQuery and Notion API surfaces are stable; Anthropic Skill best practices change occasionally but the copy-into-response checklist pattern is foundational)
