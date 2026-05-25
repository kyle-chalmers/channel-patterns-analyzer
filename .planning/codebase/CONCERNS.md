# Codebase Concerns

**Analysis Date:** 2026-05-25

This is a documentation-and-prompts repo, not a traditional application codebase. The "code" that produces the weekly report lives in an AI agent's instructions (`CLAUDE.md` + `BUSINESS_RULES.md`) rather than in executable Python. Concerns below reflect that reality: cross-document consistency, instruction precision, and the gap between documented behavior and what is actually verifiable today.

---

## Tech Debt

**Business-rules section numbering drift (highest impact):**
- Issue: `BUSINESS_RULES.md` has only four numbered sections (§1 Fiscal year start, §2 Exclude internal test channels, §3 Data health expectations, §4 Table grain and join keys). Several files reference sections that do not exist or point to the wrong section.
- Files:
  - `CLAUDE.md:91` — references `BUSINESS_RULES.md §3` for "Data Health" staleness. Correct in number, but the surrounding language ("Anything more than 3 days stale per §3") works only because §3 happens to be data health.
  - `CLAUDE.md:106` — references `BUSINESS_RULES.md §4` for table grain and join keys. Currently correct.
  - `sql/02_top_full_length_videos.sql:4` — references `BUSINESS_RULES.md §3` for the **age-control rule**. §3 is data health expectations; age control is documented in `CLAUDE.md`, not `BUSINESS_RULES.md`. Wrong reference.
  - `sql/03_age_controlled_performance.sql:2,10` — references `BUSINESS_RULES.md §3` for the age-control rule. Same problem as above.
  - `sql/04_data_health_check.sql:2` — references `BUSINESS_RULES.md §5`. §5 does not exist. Should be §3.
  - `docs/maintenance.md:9` — references `BUSINESS_RULES.md §6` for table grain. §6 does not exist. Should be §4.
  - `docs/runbook.md:31` — references `BUSINESS_RULES.md §5`. Does not exist. Should be §3.
  - `docs/runbook.md:47,57,58` — references `BUSINESS_RULES.md §6`. Does not exist. Should be §4.
- Impact: An analyzer that follows the SQL header comments will look for an age-control rule in `BUSINESS_RULES.md` and not find one (the rule is actually in `CLAUDE.md`). An operator following the runbook will look for §5/§6 and not find them. Sections look authoritative but point nowhere.
- Fix approach: Decide whether age control belongs in `BUSINESS_RULES.md` or `CLAUDE.md` (the README states `BUSINESS_RULES.md` is for "stable domain facts and data-contract rules" — age-control mechanics arguably fit there). Either move the age-control content into `BUSINESS_RULES.md` and renumber, or update every cross-reference to match the current 4-section structure. Add a `CHANGELOG.md` entry per `docs/maintenance.md` § "Evolving a business rule".

**Hardcoded `youtube_analytics` dataset name in all SQL files:**
- Issue: All four SQL files in `sql/` hardcode the literal table reference `\`youtube_analytics.<table>\``, despite the README (`README.md:198-202`) and `CLAUDE.md:106` instructing that the dataset name should come from `BQ_DATASET`.
- Files: `sql/01_latest_snapshot_overview.sql`, `sql/02_top_full_length_videos.sql`, `sql/03_age_controlled_performance.sql`, `sql/04_data_health_check.sql`.
- Impact: Anyone whose BigQuery dataset is not named `youtube_analytics` (per the README, this is most viewers) must either find-and-replace before running, or trust the analyzer to template at query time. The header comments say "the analyzer should template `${BQ_DATASET}` when it runs", but there is no templating mechanism in the repo — it is a verbal instruction to a language model.
- Fix approach: Either (a) introduce a templating step (Python or shell) that substitutes `${BQ_DATASET}` before passing SQL to `bq`, or (b) explicitly document that the analyzer must rewrite the dataset string itself before running each query, and add a verification check in `CLAUDE.md`'s run sequence to catch when this is forgotten.

**Timezone inconsistency in SQL:**
- Issue: `BUSINESS_RULES.md:38` requires staleness comparisons in America/Phoenix time. `sql/04_data_health_check.sql:9-12` notes the issue in a header comment but the actual SQL still uses bare `CURRENT_DATE()` (UTC default). `sql/02_top_full_length_videos.sql:20` and `sql/03_age_controlled_performance.sql:24,35` also use bare `CURRENT_DATE()` for the age calculation.
- Files: `sql/02`, `sql/03`, `sql/04`.
- Impact: For up to 7 hours per day (the Phoenix–UTC offset), `CURRENT_DATE()` in UTC is one day ahead of Phoenix. A video published "today" in Phoenix will show `days_since_published = 1` when it should be 0, and a snapshot pulled "yesterday" in Phoenix may register as `days_stale = 1` instead of 0 during the early-morning Phoenix hours. Edge effects on day boundaries.
- Fix approach: Replace `CURRENT_DATE()` with `CURRENT_DATE("America/Phoenix")` across all three SQL files. Add a `CHANGELOG.md` entry. Optionally parameterize via `SCHEDULE_TIMEZONE` from `.env`.

**`requirements.txt` semantic mismatch:**
- Issue: `requirements.txt:7-8` references `requirements-csv.txt` and `requirements-bigquery.txt`, but neither file exists in the repo. The current file's actual content (lines 11-19) is all comments — the CSV path uses only stdlib, and the BigQuery deps are commented out.
- Files: `requirements.txt`.
- Impact: `pip install -r requirements.txt` (which the README:98 instructs) is a no-op. Anyone following the cross-references in the file looking for `requirements-csv.txt` will fail.
- Fix approach: Either remove the cross-references and document the file's all-comments nature explicitly, or actually split into the two files the comments describe.

**`sample_data/` is gitignored but present on disk:**
- Issue: `.gitignore:33` excludes `sample_data/`, but the repo at HEAD contains `sample_data/*.csv` files (8KB of CSVs, created May 24). Either they should be committed (and `.gitignore` updated) or removed.
- Files: `.gitignore:33`, `sample_data/*.csv`.
- Impact: Untracked files clutter the working tree. New clones will not have sample data until they run `scripts/csv_fallback_loader.py`, which is the intended flow — but the local repo state shows generated artifacts hanging around. If the README ever changes to say "sample data ships with the repo", the `.gitignore` will silently prevent that.
- Fix approach: Confirm intent. If sample data should ship, remove the `.gitignore` entry. If it should be generated locally only, leave the `.gitignore` and just delete the untracked CSVs from the working tree before commits.

**`scripts/csv_fallback_loader.py` writes timestamps relative to "today":**
- Issue: `scripts/csv_fallback_loader.py:145` uses `date.today()` (system local time) as the snapshot date, and computes each video's `published_at` as `(today - days_ago).isoformat() + "Z"` (`:55`). Appending `"Z"` claims UTC, but the timestamp is constructed in local time. The result is a UTC-labeled timestamp that is actually local-time. Drift is up to 24 hours depending on the runner's timezone.
- Files: `scripts/csv_fallback_loader.py:55, 145`.
- Impact: For viewers in non-UTC timezones using the CSV fallback, the published-at timestamps are wrong by a few hours, which can flip a video's `days_since_published` boundary check (the 14-day low-confidence cutoff is exactly this kind of boundary). The VID013 test case (3 days old) is robust to this; the VID012 case (6 days old) probably is too; but a video at exactly 14 days old could land on either side.
- Fix approach: Use `datetime.now(timezone.utc).date()` for `today`, or strip the `"Z"` suffix and use a naive timestamp. Adding `from datetime import timezone` and explicit UTC construction is the cleanest fix.

**Unused environment variables documented in `.env.example`:**
- Issue: `.env.example` defines `YOUTUBE_CHANNEL_ID`, `ANALYSIS_LOOKBACK_DAYS`, `MIN_VIDEO_AGE_DAYS`, and `SCHEDULE_TIMEZONE`, but none of these are referenced anywhere in `sql/`, `scripts/`, `CLAUDE.md`, or `BUSINESS_RULES.md`. `MIN_VIDEO_AGE_DAYS=14` exists as a value, but the actual 14-day threshold is hardcoded in `CLAUDE.md` and `sql/03_age_controlled_performance.sql:35`.
- Files: `.env.example:23, 32, 35, 39`.
- Impact: An operator who changes `MIN_VIDEO_AGE_DAYS=21` in their `.env` will see no effect, because the rule is hardcoded in two other places. Same for the lookback window and timezone. This is exactly the silent-threshold-drift problem the global CLAUDE.md warns against.
- Fix approach: Either remove unused env vars from `.env.example`, or actually wire them through. If the analyzer is supposed to template SQL with `BQ_DATASET`, the same templating step can substitute `MIN_VIDEO_AGE_DAYS` for the `>= 14` literal.

---

## Known Bugs

**`sql/01_latest_snapshot_overview.sql` checks only two tables for "latest common snapshot":**
- Symptoms: The header (`sql/01_latest_snapshot_overview.sql:11-13`) describes the query as taking `MIN(MAX(snapshot_date))` across the source tables. The actual `LEAST(...)` in lines 16-19 spans only `video_metadata` and `daily_video_stats`. `BUSINESS_RULES.md:54-55` defines the latest common snapshot as "MIN(MAX(snapshot_date)) across all source tables" (four tables).
- Files: `sql/01_latest_snapshot_overview.sql:15-19`.
- Trigger: When `daily_video_analytics` or `daily_traffic_sources` is materially staler than the other two, this query will still report a `latest_snapshot` that no longer represents "the latest day where ALL tables have data." Downstream analyses joining all four tables will then silently shrink or skip rows.
- Workaround: The data-health check in `sql/04` does cover all four tables, so the staleness will surface — but the "overview" query's number is misleading.
- Fix: Extend the `LEAST(...)` to include `daily_video_analytics` and `daily_traffic_sources`, or rename the column and tighten the header comment to match the two-table scope.

**`days_since_published` uses snapshot table's `MAX(snapshot_date)` to filter the metadata side only:**
- Symptoms: `sql/02_top_full_length_videos.sql:27-29` and `sql/03_age_controlled_performance.sql:31-33` filter both `m` and `s` to `m.snapshot_date = (SELECT MAX(snapshot_date) FROM video_metadata)`. If `daily_video_stats` has a different latest snapshot than `video_metadata`, the `JOIN ... USING (video_id, snapshot_date)` will silently drop rows where stats arrived on a different cadence.
- Files: `sql/02_top_full_length_videos.sql:27-29`, `sql/03_age_controlled_performance.sql:31-33`.
- Trigger: Any day when the upstream pipeline lands the two tables out of sync — a real possibility per the runbook's mention of `daily_video_analytics` being currently stale (`PROMPTS.md:94`).
- Workaround: None silent. Operator must check `summary.json` and confirm both snapshot dates match before trusting the query.
- Fix: Use the "latest common snapshot" pattern from `sql/01` (extended to cover the joined tables) instead of just `video_metadata`'s latest. Document in `BUSINESS_RULES.md` §4.

---

## Security Considerations

**`bq` CLI runs with the operator's full BigQuery identity:**
- Risk: The analyzer instructed via `CLAUDE.md:106` to run `bq query --use_legacy_sql=false` inherits whatever IAM permissions the signed-in user has — typically far broader than read-only access to one dataset. A prompt-injected instruction (e.g., embedded in a video title pulled from BigQuery) could trigger a destructive query.
- Files: `CLAUDE.md:106`, `docs/runbook.md` (no scoping guidance).
- Current mitigation: None in the repo. The README recommends `roles/bigquery.dataViewer` (`README.md:193`), but does not enforce it.
- Recommendations: (1) Document the minimum-permissions principle in the setup section, recommending a dedicated read-only service account for routine runs. (2) Add a guardrail in `CLAUDE.md`: the analyzer must only run `SELECT` queries and must refuse any DDL/DML, even if instructed. (3) For the cloud routine, require a service-account key scoped to `roles/bigquery.dataViewer` + `roles/bigquery.jobUser`, not a personal account.

**Public-repo notice missing despite `.internal/` setup:**
- Risk: The global `CLAUDE.md` rule for public-facing repos requires a notice at the top of project-level `CLAUDE.md` warning the agent that the repo is public-facing. This repo has `.internal/` configured (per `.gitignore:5`) and the README explicitly states it is a YouTube companion (`README.md:5`), but neither `CLAUDE.md` nor `BUSINESS_RULES.md` carries the "public-facing repo" notice.
- Files: `CLAUDE.md` (top), `.gitignore:5`.
- Current mitigation: `.gitignore` blocks `.internal/`, `.env`, `*credentials*.json`, `client_secret.json`. Coverage is good.
- Recommendations: Add the standard public-facing notice (per the user's global CLAUDE.md) to the top of project `CLAUDE.md`. Without it, a future Claude session may not know to keep recording-prep content out of generated reports or commits.

**No secrets in committed files (verified):**
- Risk: Low.
- Current mitigation: `.gitignore` excludes `.env`, `.env.*`, `.internal/`, `client_secret.json`, `*credentials*.json`. `.env.example` contains only placeholder values (`your-gcp-project-id`, `UCxxxxxxxxxxxxxxxxxx`). No actual credentials observed in any committed file.
- Recommendations: None additional beyond the public-repo notice above.

---

## Performance Bottlenecks

**Not applicable at current scale.** The repo's dataset is ~24 videos × small number of snapshot dates. All four SQL queries scan trivially small partitions. No bottleneck to report. The maintenance doc (`docs/maintenance.md:10`) already calls out the right concern: revisit if a query ever returns thousands of rows.

**Latent concern: `LIMIT 20` ceiling in top-videos queries:**
- Problem: `sql/02_top_full_length_videos.sql:32` and `sql/03_age_controlled_performance.sql:47` cap at 20 rows. The dataset has ~24 full-length videos today. As the channel grows past 20 full-length videos with age ≥ 14, the analyzer will silently miss the long tail.
- Files: `sql/02:32`, `sql/03:47`.
- Cause: Hardcoded limit, not derived from `total_videos`.
- Improvement path: Either remove the `LIMIT` (the dataset is small enough) or document explicitly that the analyzer should remove or raise the limit when the full-length count exceeds 20 (which will be reported in `summary.json`'s `video_count_full_length` field per `runs/README.md:48`).

---

## Fragile Areas

**The analyzer's behavior is fully dependent on `CLAUDE.md` being loaded correctly:**
- Files: `CLAUDE.md`, `BUSINESS_RULES.md`.
- Why fragile: There is no executable code that enforces age control, small-sample hedging, or the report structure. All of it is prose instructions to a language model. A change in how Claude Code loads `CLAUDE.md` (e.g., context-window pressure dropping the file's middle sections) silently degrades the report's quality without any error surface. The repo has no test that verifies a generated report respects the rules.
- Safe modification: Keep `CLAUDE.md` short enough to fit comfortably in context (currently 135 lines, well within limits). When adding rules, prefer adding to `BUSINESS_RULES.md` (currently 55 lines) over expanding `CLAUDE.md` so the data-contract rules survive even if voice/style guidance is truncated.
- Test coverage: Zero. No automated check that the analyzer hedges small samples, applies age control, or emits the required report sections.

**Cross-document section numbering (covered above) is a fragility multiplier:**
- Why fragile: Any future edit to `BUSINESS_RULES.md` that renumbers a section will silently break references across `CLAUDE.md`, four SQL header comments, and two docs files. There is no link-check.
- Safe modification: Reference rules by section title (e.g., "data health expectations") rather than section number wherever possible. When a number must be used, add a unit test or a CI grep that fails when the referenced section is missing.

**`runs/{date}/summary.json` is hand-written by the analyzer:**
- Files: `runs/README.md:30-57`, `CLAUDE.md:117-118`.
- Why fragile: The schema in `runs/README.md` is documentation, not enforced. The analyzer writes the JSON itself based on prose instructions. A run that drops the `errors` field, mis-formats a date, or skips `notion_write_ok` will not be caught until someone tries to audit it months later.
- Safe modification: Either ship a JSON schema and have the analyzer validate before write, or accept the drift risk explicitly. At minimum, the runbook should include a "summary.json structural check" step before declaring a run successful.

**Notion write is delegated to a Skill that is gitignored:**
- Files: `.gitignore:39` (`.claude/skills/`), `CLAUDE.md:14` ("The skill handles the write"), `README.md:30, 305-310`.
- Why fragile: The `write-notion-report` Skill is built live during the video and never committed. Every fresh clone of the repo has zero implementation of the Notion-publishing step. The analyzer's instruction to "hand the report to the `write-notion-report` skill" will fail silently in any environment where that Skill has not been generated. Per `CLAUDE.md:14`: "Do not try to call Notion directly" — so there is no fallback.
- Safe modification: Either commit a reference version of the Skill (perhaps under `examples/`) or add an explicit pre-flight check in the analyzer's run sequence: "Confirm `.claude/skills/write-notion-report/SKILL.md` exists; if not, fail with a clear setup error pointing to PROMPTS.md Prompt 7." Currently the analyzer would discover the missing Skill only at the final step, after running all the queries.

**The CSV fallback uses `date.today()` baking the dataset to the day of generation:**
- Files: `scripts/csv_fallback_loader.py:145, 51-63`.
- Why fragile: Sample CSVs generated on day X have a snapshot date of X. If a user generates them, sets `DATA_SOURCE=csv`, and runs the analyzer two weeks later, the data-health check will (correctly) flag all four tables as stale by 14 days. New users debugging "why is my fallback always flagged stale?" hit this naturally.
- Safe modification: Document in the README that the CSV fallback should be regenerated for each analyzer run, or have the loader accept a `--snapshot-date` argument so the fallback can be regenerated cheaply.

---

## Scaling Limits

**Channel video count:**
- Current capacity: ~24 full-length videos.
- Limit: The small-sample thresholds in `CLAUDE.md:73-78` (5 / 10 / standard) are well-suited for a small channel. Past ~50 full-length videos, the "moderate confidence" band becomes the floor for almost every claim and the hedging language stops adding signal.
- Scaling path: Re-tune confidence thresholds when total full-length video count exceeds 50. Log in `CHANGELOG.md` per `docs/maintenance.md` § "Evolving a business rule".

**Per-run query artifact size:**
- Current capacity: `runs/{date}/queries/*.json` is committed to git. With ~24 videos × 4 tables, raw JSON dumps are well under 100KB total.
- Limit: `docs/maintenance.md:10` flags "multi-MB is not [fine]" as the soft ceiling. Single-table JSON for, say, daily snapshots over a year (~24 × 365 × 4 tables) would push toward 5-10MB and bloat the git history.
- Scaling path: When per-run artifacts cross ~1MB, either compress before commit or move to a separate gitignored cache + Git LFS for selected runs.

---

## Dependencies at Risk

**`bq` CLI behavior dependency:**
- Risk: The analyzer is one of the few systems left in the Google ecosystem where the official recommendation is to drive a CLI from another process rather than use a client library. Google has progressively de-emphasized `bq` in favor of the Python/Go clients. If `bq` is removed from a future Google Cloud SDK release, the entire analyzer breaks.
- Impact: Total analyzer outage; no fallback in the repo.
- Migration plan: The `requirements.txt:17-18` commented-out block already lists `google-cloud-bigquery>=3.20.0`. Switching from CLI to library is a one-day effort: write a thin Python wrapper that takes the same SQL string and returns the same JSON shape. Schedule this work before the channel depends on the cloud routine in production.

**Claude Code `/schedule` routines were shipped April 14, 2026 (per `README.md:360`):**
- Risk: A new product feature this early in its lifecycle may change config format, env-var semantics, or pricing. The repo's `routine_config.json` is gitignored and rebuilt by the video, so existing routines won't auto-update.
- Impact: A scheduled run silently stops firing, or fires but cannot find the repo / env vars after a routine-config schema change.
- Migration plan: Subscribe to Claude Code release notes. When `/schedule` ships breaking changes, rebuild via Prompt 10.

**Notion MCP vs. web connector divergence:**
- Risk: The Notion MCP server and the Claude.com Notion connector are independently maintained surfaces (`README.md:208-209`, `docs/schedule.md:17-27`). They have already drifted (local MCP for terminal, web connector for cloud). A future change to either could break one path while leaving the other working.
- Impact: Local development continues to work; scheduled cloud runs fail silently, or vice versa.
- Migration plan: The runbook (`docs/runbook.md:67-76`) already documents both paths. Add a smoke test step to "after every cloud-routine config change, fire `Run now` once before relying on the schedule."

---

## Missing Critical Features

**No way to verify a published report actually matches `reports/{date}.md`:**
- Problem: `CLAUDE.md:113-114` says the same content should land in Notion and in `reports/{date}.md`, but there is no diff check. If the Skill silently truncates or reformats the report, the archive and the published version drift.
- Blocks: The audit-trail promise in `runs/README.md:18-26` ("the difference between 'the analyzer said it' and 'the analyzer said it and here's why'"). If the Notion page diverges, the archive no longer answers what was actually published.

**No automated check that `runs/{date}/summary.json` exists after a run:**
- Problem: `CLAUDE.md:117-118` and `runs/README.md:59` both insist `summary.json` must be written on every run, including failures. There is no check that this actually happened. A run that crashes before the summary write leaves no audit trail and no error surface.
- Blocks: Post-mortem analysis when a scheduled run silently fails.

**No mechanism to enforce "read recent reports" before drafting:**
- Problem: `CLAUDE.md:113-114` instructs the analyzer to read the most recent 3-4 reports before drafting. With no enforcement, a context-pressured session might skip it. The result is a report that re-states findings verbatim or fails to upgrade confidence as the sample grows.
- Blocks: The cross-week calibration promise.

---

## Test Coverage Gaps

This repo has no test suite. Everything below would be valuable to add; nothing exists today.

**No tests for `scripts/csv_fallback_loader.py`:**
- What is not tested: Schema match with BigQuery tables, deterministic output across runs (seeds are set inline at `:69, :89, :116`, so output is reproducible but not asserted), CSV header order, type coercion for `published_at`.
- Files: `scripts/csv_fallback_loader.py`.
- Risk: A future refactor changes a column name and the analyzer's CSV path breaks. The CSV schema is supposed to "match the BigQuery table schemas exactly" (`PROMPTS.md:81`); nothing checks this.
- Priority: Medium. Low impact unless the CSV fallback is the primary demo path.

**No SQL linting or query-validity check:**
- What is not tested: That the four SQL files in `sql/` parse against the BigQuery dialect; that referenced columns exist in the documented schema; that join keys produce expected cardinality.
- Files: `sql/*.sql`.
- Risk: A SQL file with a typo (e.g., `view_count` vs `views_count`) reaches production unnoticed because the only way to verify is to run against real BigQuery.
- Priority: Medium. Add a `bq query --dry_run` step against a test project, or use a tool like SQLFluff with the BigQuery dialect.

**No end-to-end "report respects business rules" test:**
- What is not tested: That a generated report includes the Data Health section first; that it labels small-sample claims with confidence; that it excludes videos with `days_since_published < 14` from top-performers.
- Files: All of `CLAUDE.md`'s rules.
- Risk: The analyzer drifts from its own rules. Hard to detect because the output is prose.
- Priority: High. A LLM-as-judge eval pass over a generated report against the rules in `CLAUDE.md` would catch regressions and be cheap to run as part of a routine. This is the highest-leverage test for this repo.

**No link-and-section-number check across docs:**
- What is not tested: That every `BUSINESS_RULES.md §N` reference points to a section that actually exists.
- Files: `CLAUDE.md`, `docs/runbook.md`, `docs/maintenance.md`, `sql/*.sql`.
- Risk: Documented above as the highest-impact tech debt item; broken references already exist today.
- Priority: High. A grep-based CI check is one line of bash.

---

*Concerns audit: 2026-05-25*
