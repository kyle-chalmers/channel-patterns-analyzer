# Phase 3 Cloud Smoke Test (SCHED-02)

**Status:** awaiting operator execution. The executor that ran Plan 03-04 (commit hashes in `03-04-SUMMARY.md`) cannot execute this smoke test because it is on a different account than the one that owns the cloud routine. Tasks 1 through 5 of Plan 03-04 are fully completed and committed; this file is the staged template the operator fills in before `/gsd-verify-phase` is re-run.

**Goal:** verify the live cloud routine produces an end-to-end report against the production Notion page on the production BigQuery dataset, with all six required sections and a clean `errors: []` array in `summary.json`. This is the Phase 3 SCHED-02 (cloud routine smoke test) acceptance gate.

**Cadence:** runs once. After this test passes, the weekly Monday-9am-Phoenix routine starts producing reports without further smoke testing.

---

## Setup

Confirm the following are true before clicking Run now in the Anthropic UI. Each line is a yes/no check.

- [ ] [OPERATOR: fill after running cloud smoke test] BigQuery (Google Cloud) connector authorized at claude.com, Settings, Connectors. Connector shows access to the GCP project named in `BQ_PROJECT`.
- [ ] [OPERATOR: fill after running cloud smoke test] Notion connector authorized at claude.com, Settings, Connectors. Connector shows access to the page named by `NOTION_REPORT_PAGE_ID`.
- [ ] [OPERATOR: fill after running cloud smoke test] Routine `channel-patterns-analyzer-weekly` exists at claude.com, Settings, Routines.
- [ ] [OPERATOR: fill after running cloud smoke test] Routine Instructions field contains the imperative prompt that points the routine at `.claude/commands/run-analyzer.md` (per `docs/schedule.md` § "Cloud routine setup walkthrough" step 4).
- [ ] [OPERATOR: fill after running cloud smoke test] Routine Repositories field includes `kyle-chalmers/channel-patterns-analyzer`.
- [ ] [OPERATOR: fill after running cloud smoke test] Routine Trigger is Schedule, Weekly, Monday, 9:00 AM, America/Phoenix.
- [ ] [OPERATOR: fill after running cloud smoke test] Routine environment variables include `NOTION_REPORT_PAGE_ID`, `BQ_PROJECT`, `BQ_DATASET` (per `docs/schedule.md` § "Cloud routine setup walkthrough" step 8).

**Cloud run URL (paste after Run now is clicked):** [OPERATOR: fill after running cloud smoke test]

**Run start time (Phoenix):** [OPERATOR: fill after running cloud smoke test]
**Run end time (Phoenix):** [OPERATOR: fill after running cloud smoke test]

---

## Run-now checklist results

Items (a) through (d) mirror `docs/schedule.md` § "Run-now checklist". For each item, paste the verification evidence into the placeholder.

### (a) New Notion child page appears

**Required evidence:** the URL of the new child page under the channel-patterns parent, plus the page title (`Weekly report, {today's Phoenix date}`).

- [ ] [OPERATOR: fill after running cloud smoke test] New child page URL: ______
- [ ] [OPERATOR: fill after running cloud smoke test] Page title matches `Weekly report, YYYY-MM-DD` Phoenix-date convention: yes / no
- [ ] [OPERATOR: fill after running cloud smoke test] Appeared within 60 seconds of "Run now" click: yes / no
- [ ] [OPERATOR: fill after running cloud smoke test] If "no" on any of the above, name the runbook section consulted (e.g. `docs/runbook.md` § "Notion connector not authorized"): ______

### (b) Notion page renders all six sections with intact (label, n=N) parentheticals

**Required evidence:** confirmation that each of the six required headings renders, plus one example `(label, n=N)` parenthetical pasted verbatim from the published page.

- [ ] [OPERATOR: fill after running cloud smoke test] Data Health section present: yes / no
- [ ] [OPERATOR: fill after running cloud smoke test] Headline section present: yes / no
- [ ] [OPERATOR: fill after running cloud smoke test] What is working section present: yes / no
- [ ] [OPERATOR: fill after running cloud smoke test] What is not working section present: yes / no
- [ ] [OPERATOR: fill after running cloud smoke test] Patterns worth watching section present: yes / no
- [ ] [OPERATOR: fill after running cloud smoke test] Open questions section present: yes / no
- [ ] [OPERATOR: fill after running cloud smoke test] One sample `(label, n=N)` parenthetical pasted from the page: ______
- [ ] [OPERATOR: fill after running cloud smoke test] Notion rendered the parenthetical as plain text (not stripped, not linkified): yes / no

### (c) Anthropic UI shows the run as completed and no category error lines

**Required evidence:** the run's status badge from the Anthropic UI, plus a confirmation that scanning the transcript surfaces zero `category: ...` lines.

- [ ] [OPERATOR: fill after running cloud smoke test] Anthropic UI status badge: completed (green) / errored / canceled
- [ ] [OPERATOR: fill after running cloud smoke test] Transcript scanned for `category:` strings; count of `category: ...` error lines: ______
- [ ] [OPERATOR: fill after running cloud smoke test] If the run timed out or hung, name the runbook section consulted (e.g. `docs/runbook.md` § "Routine run timed out or hung"): ______
- [ ] [OPERATOR: fill after running cloud smoke test] If the UI showed an infrastructure error before the recipe ran, name the runbook section consulted (e.g. `docs/runbook.md` § "Anthropic UI shows error before recipe runs"): ______

### (d) Local artifact verification after the cloud branch lands

**Required evidence:** the contents of `summary.json` from the run, specifically `notion_write_ok`, the `errors[]` array, the snapshot dates per table, and the BigQuery transport branch selected.

- [ ] [OPERATOR: fill after running cloud smoke test] Branch name where the cloud routine pushed artifacts (`claude/...`): ______
- [ ] [OPERATOR: fill after running cloud smoke test] After `git pull` of that branch, `runs/{date}/summary.json` exists: yes / no
- [ ] [OPERATOR: fill after running cloud smoke test] `summary.json.notion_write_ok`: true / false
- [ ] [OPERATOR: fill after running cloud smoke test] `summary.json.errors[]` array length: ______
- [ ] [OPERATOR: fill after running cloud smoke test] If non-empty, each error's `category` and the runbook section consulted: ______
- [ ] [OPERATOR: fill after running cloud smoke test] `summary.json.transport`: bq_cli / bq_mcp / csv (expected: `bq_mcp` for cloud routine)
- [ ] [OPERATOR: fill after running cloud smoke test] `summary.json.snapshot_dates` (paste the map): ______
- [ ] [OPERATOR: fill after running cloud smoke test] `summary.json.voice_audit.checks_passed` is non-empty (Step 7 self-audit ran): yes / no
- [ ] [OPERATOR: fill after running cloud smoke test] `reports/{date}.md` also landed in the pushed branch: yes / no

---

## Outcome

Mark one of the three outcomes below. If "partial pass" or "fail", the runbook section consulted for each failed item is captured in items (a) through (d) above.

- [ ] [OPERATOR: fill after running cloud smoke test] **Pass.** All four checklist items returned the expected evidence; no runbook section was consulted because no failure was hit. Phase 3 SCHED-02 acceptance gate cleared. The weekly Monday-9am Phoenix routine is live.
- [ ] [OPERATOR: fill after running cloud smoke test] **Partial pass.** One or more checklist items returned a failure, but every failure was named by a `docs/runbook.md` section (ERR-01 holds) and was resolved before the test was re-run. Re-run results pasted in the placeholders above. Phase 3 SCHED-02 acceptance gate cleared.
- [ ] [OPERATOR: fill after running cloud smoke test] **Fail.** A failure mode was hit that is not in `docs/runbook.md`. ERR-03 requires adding the new section as part of the fix; do that, log it in `CHANGELOG.md`, and re-run this smoke test. Phase 3 cannot transition to done until this stub records a pass or partial-pass.

**Operator notes (anything the test surfaced that the runbook should learn from):**

[OPERATOR: fill after running cloud smoke test]

---

## Provenance

- Plan 03-04 Tasks 1 through 5: completed by Plan 03-04 executor. See `.planning/phases/03-csv-parity-and-operational-polish/03-04-SUMMARY.md` for commit hashes.
- This stub: scaffolded by Plan 03-04 executor on 2026-05-25 awaiting operator-side cloud run. The executor cannot run the cloud routine because it is on a different account than the one that owns the routine in claude.com.
- Verification: `/gsd-verify-phase` will not pass Phase 3 until every `[OPERATOR: fill after running cloud smoke test]` placeholder is replaced with real evidence and an outcome is marked.
