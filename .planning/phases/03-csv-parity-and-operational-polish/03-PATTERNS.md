# Phase 3: CSV Parity and Operational Polish - Pattern Map

**Mapped:** 2026-05-25
**Files analyzed:** 7 files Phase 3 touches (one new, six modified)
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/csv_query.py` (NEW) | utility / data-engine | batch (CSV-in → JSON-out) | `scripts/csv_fallback_loader.py` (in-repo stdlib pattern) AND `runs/2026-05-25/queries/data_health.json` (shape contract) | exact (stdlib script) + exact (output shape) |
| `scripts/csv_fallback_loader.py` (MOD) | utility / fixture-generator | batch (deterministic CSV write) | itself — fix-in-place at `:55` (UTC) and `:145` (`date.today()`), add `--snapshot-date` arg using stdlib `argparse` | self-modification |
| `.claude/commands/run-analyzer.md` (MOD) | recipe / orchestrator | request-response (slash command, one linear recipe) | itself — Step 1 transport probe (lines 20-34) is the analog for adding the `DATA_SOURCE=csv` branch; Step 2/3/5 dispatch lines (lines 36-115) are the analog for invoking the CSV helper | self-extension |
| `docs/schedule.md` (MOD) | documentation / operator manual | static doc | itself — keep "What the routine does" + "Local vs cloud" framing (lines 5-27); expand the cloud column with a numbered walkthrough + Run-now checklist | self-extension |
| `docs/runbook.md` (MOD) | documentation / failure-mode playbook | static doc | `docs/runbook.md` existing sections — every new section follows the Symptom / Fix / Recording template (lines 9-25 for the canonical example) | exact (template lives in the same file) |
| `.env.example` (MOD) | configuration | static config | itself — keep the boxed-divider comment style (`# ─── Title ───`); remove unused vars per CONCERNS.md | self-modification |
| `CHANGELOG.md` (MOD) | documentation / audit log | append-only log | itself — every CHANGELOG entry is a dated H2 (`## 2026-05-25`) followed by bullet lines; Phase 3 appends new H2 sections | exact |

---

## Pattern Assignments

### `scripts/csv_query.py` (NEW — utility, batch)

**Analog 1: `scripts/csv_fallback_loader.py`** — for the stdlib-only Python script shape, file header docstring, `Path(__file__).resolve().parent.parent` repo-root pattern, `if __name__ == "__main__": main()` entrypoint, and stdlib-only imports (`csv`, `os`, `random`, `datetime`, `pathlib`).

**File-header docstring pattern** (`scripts/csv_fallback_loader.py:1-10`):

```python
"""Generate a sample CSV dataset that mimics the youtube_analytics BigQuery schema.

Useful for following along with the analyzer without setting up the full
youtube-bigquery-pipeline. Output goes to sample_data/ and matches the schema
of the four BigQuery tables (video_metadata, daily_video_stats,
daily_video_analytics, daily_traffic_sources).

Usage:
    python scripts/csv_fallback_loader.py
"""
```

**Stdlib imports + repo-root + sample dir** (`scripts/csv_fallback_loader.py:12-19`):

```python
import csv
import os
import random
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO_ROOT / "sample_data"
```

Apply this verbatim in `csv_query.py`. Add `import argparse`, `import json`, and `import sys` for the new helper's needs. Drop `random` (the query helper is deterministic by virtue of reading deterministic fixtures, not generating new ones).

**Function-per-table pattern** (`scripts/csv_fallback_loader.py:49-129`):

```python
def generate_video_metadata(snapshot: date) -> list[dict]:
    rows: list[dict] = []
    for vid, title, dur, vtype, days_ago in SAMPLE_VIDEOS:
        rows.append({
            "video_id": vid,
            ...
            "snapshot_date": snapshot.isoformat(),
        })
    return rows
```

Mirror this shape in `csv_query.py` with one function per query identifier: `query_data_health(...) -> list[dict]`, `query_top_full_length_videos(...) -> list[dict]`, `query_eligible_video_count(...) -> list[dict]`. Each returns a `list[dict]` ready to JSON-dump.

**Entrypoint** (`scripts/csv_fallback_loader.py:144-160`):

```python
def main() -> None:
    snapshot = date.today()
    print(f"Generating sample data for snapshot_date = {snapshot}")
    ...

if __name__ == "__main__":
    main()
```

Replace with an `argparse`-driven entrypoint accepting a positional `query_name` arg (one of `data_health`, `top_full_length_videos`, `eligible_video_count`) plus `--sample-dir` (default `sample_data/`). Dispatch to the matching `query_*` function, JSON-dump to stdout via `json.dump(rows, sys.stdout)`.

---

**Analog 2: `runs/2026-05-25/queries/data_health.json` (live shape contract)**

**JSON output shape** (live BigQuery `bq query --format=json` result):

```json
[
  {"days_stale":"0","latest_snapshot":"2026-05-25","table_name":"daily_video_stats"},
  {"days_stale":"0","latest_snapshot":"2026-05-25","table_name":"video_metadata"},
  {"days_stale":"0","latest_snapshot":"2026-05-25","table_name":"daily_video_analytics"},
  {"days_stale":"0","latest_snapshot":"2026-05-25","table_name":"daily_traffic_sources"}
]
```

Critical conventions the CSV helper must match (per RESEARCH.md "CSV Output JSON Shape Contract"):

1. **Top-level is a JSON array**, not `{"rows": [...]}`. Step 1 of the recipe handles the MCP wire-shape conversion; the on-disk artifact is always an array.
2. **All values are JSON strings.** `days_stale` is `"0"`, not `0`. `view_count` is `"10271"`, not `10271`. BigQuery's `--format=json` coerces numerics to strings; the helper must do the same. Python's `csv.DictReader` returns strings naturally, so this is a happy accident — but integer-typed fields computed in Python (e.g., `days_stale = (today - snapshot).days`) must be wrapped with `str(...)` before writing.
3. **Column names match the SQL `SELECT` aliases verbatim.** Order is not guaranteed.

**Reference shape for `top_full_length_videos.json`** (one row example, from `runs/2026-05-25/queries/top_full_length_videos.json`):

```json
{"comment_count":"7","days_since_published":"199","duration_formatted":"26:50","like_count":"111","published_at":"2025-11-07 13:01:07","title":"Claude Code vs Manual Jira Ticket Work | The Difference Is Amazing","video_type":"full_length","view_count":"10271"}
```

The helper produces these keys in the same string-coerced form.

**Reference shape for `eligible_video_count.json`** (per recipe lines 94-111 — three columns):

```json
[{"eligible_count":"18","total_full_length":"23","latest_common_snapshot":"2026-05-25"}]
```

One-row array, three string-valued keys.

**Date arithmetic note** — the eligible-count query uses `DATE_DIFF(CURRENT_DATE("America/Phoenix"), DATE(m.published_at), DAY) >= 14`. The CSV helper reimplements this in Python with `datetime` + a fixed `ZoneInfo("America/Phoenix")` (stdlib `zoneinfo`, Python 3.9+). Read `published_at` strings with `datetime.fromisoformat()` (the loader writes ISO-format timestamps with a trailing `Z` — strip the `Z` before parsing, or replace `Z` with `+00:00`).

---

### `scripts/csv_fallback_loader.py` (MOD — utility, batch)

**Self-modification:** Phase 3 changes two lines and adds an `argparse`-driven `--snapshot-date` arg.

**Bug 1 — line 55** (`scripts/csv_fallback_loader.py:55`):

```python
"published_at": (datetime.combine(snapshot, datetime.min.time()) - timedelta(days=days_ago)).isoformat() + "Z",
```

The trailing `"Z"` falsely labels a naive timestamp as UTC. Either (a) attach a real timezone (`ZoneInfo("America/Phoenix")`) and emit `+isoformat()` without the manual `Z`, or (b) build the timestamp in UTC explicitly. Recommend (a) for consistency with the rest of the project's Phoenix-anchored time logic.

**Bug 2 — line 145** (`scripts/csv_fallback_loader.py:144-146`):

```python
def main() -> None:
    snapshot = date.today()
    print(f"Generating sample data for snapshot_date = {snapshot}")
```

`date.today()` returns the system-local date, not the Phoenix date — could differ when the operator's machine is in a different timezone. Replace with Phoenix-anchored equivalent:

```python
from zoneinfo import ZoneInfo
snapshot = datetime.now(ZoneInfo("America/Phoenix")).date()
```

**New: `--snapshot-date` arg** (no in-repo argparse analog yet — apply stdlib pattern):

```python
import argparse

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate sample CSV fixtures.")
    parser.add_argument(
        "--snapshot-date",
        type=date.fromisoformat,
        default=None,
        help="Override the snapshot date (YYYY-MM-DD). Defaults to today's Phoenix date.",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    snapshot = args.snapshot_date or datetime.now(ZoneInfo("America/Phoenix")).date()
    ...
```

---

### `.claude/commands/run-analyzer.md` (MOD — recipe, request-response orchestrator)

**Self-extension:** Phase 3 modifies Step 1 (transport probe) and the dispatch lines in Steps 2, 3, 5 to add the CSV branch. Also dereferences six `.planning/` prose references (per RESEARCH.md "Cloud-Portability Audit" lines 82-93).

**Step 1 transport probe — analog for the third branch** (`.claude/commands/run-analyzer.md:20-34`):

```markdown
## Step 1: Probe transports

Probe the session for an available BigQuery transport, in this order:

- Try `command -v bq` via Bash. If `bq` is on PATH, set `TRANSPORT=bq_cli`.
- Else check whether `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly` is loaded in the session. If yes, set `TRANSPORT=bq_mcp`.
- Else write `runs/{run_date}/summary.json` with `errors: [{"category": "no_bigquery_transport", "message": "neither bq CLI nor BigQuery MCP available", "step": "transport_probe"}]` and STOP.
```

**Apply this shape for the CSV branch.** Per RESEARCH.md Open Question 3 (short-circuit recommendation), the CSV branch comes BEFORE the `bq` probe:

```markdown
- If `DATA_SOURCE=csv`, set `TRANSPORT=csv` and skip the BigQuery probe. Before Step 2, run `python scripts/csv_fallback_loader.py` (with no `--snapshot-date` arg) to regenerate `sample_data/*.csv` for today's Phoenix snapshot.
- Else try `command -v bq` ... (existing two branches unchanged)
```

**Dispatch invocation shape — analog at lines 28-32** (`.claude/commands/run-analyzer.md:28-32`):

```markdown
- `bq_cli`: `printf '%s' "$SQL" | bq --format=json query --use_legacy_sql=false --project_id="$BQ_PROJECT"`. SQL goes in via **stdin pipe**, never as a positional argument. ...
- `bq_mcp`: invoke `mcp__claude_ai_Google_Cloud_BigQuery__execute_sql_readonly` with arguments `{"projectId": "<BQ_PROJECT value>", "query": "<SQL string>"}`. ...
```

**Add a third bullet** describing the CSV invocation:

```markdown
- `csv`: `python scripts/csv_query.py <query_name>` where `<query_name>` is one of `data_health`, `top_full_length_videos`, `eligible_video_count`. The helper reads `sample_data/*.csv`, applies the same filters/joins as the corresponding `sql/*.sql` file (or, for `eligible_video_count`, the inline SQL in Step 5), and emits a JSON array to stdout in the same shape `bq --format=json query` produces (top-level array, all values as JSON strings, column names matching the SQL aliases). No `--project_id` or dataset arg — CSV mode is project-agnostic.
```

**Dispatch call sites — Steps 2, 3, 5** (`.claude/commands/run-analyzer.md:40, 59, 113`):

Three places where the recipe says "Dispatch ... to `$TRANSPORT`" or "Dispatch via `$TRANSPORT`". Each call site needs a sentence that says: "When `$TRANSPORT=csv`, the dispatch invokes `python scripts/csv_query.py <name>` and captures stdout to the same `runs/{run_date}/queries/<name>.json` path. No `.stderr` sidecar (Python stderr is empty on success; on failure, the recipe captures the traceback into the error block)."

**Six `.planning/` references to dereference** (per RESEARCH.md table at lines 82-93):

| Line | Current text | Replacement |
|------|--------------|-------------|
| 67 | "This step implements ANALYSIS-05 and D-08 from `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`" | "This step implements the prior-report calibration rule (don't cite prior reports in prose; banned phrases listed below)." |
| 133 | "(per `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`)" | Remove the parenthetical. |
| 144 | "Apply D-08 from `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`" | "Apply the prior-report citation rule." |
| 213 | "This step implements D-01 Layer 2 from `.planning/phases/02-honest-analyst-depth/02-CONTEXT.md`" | "This step verifies the voice and structural rules were applied. The Step 6 draft made the rules explicit at draft time; this step verifies the rules were actually followed." |
| 215 | "(cited in `.planning/phases/02-honest-analyst-depth/02-RESEARCH.md` § 'Common Pitfalls' 3)" | Remove the parenthetical. |
| 215 | "mirrors `CLAUDE.md` and `02-CONTEXT.md` rules 1:1" | "mirrors `CLAUDE.md` rules and the Phase 2 decision record 1:1" |

---

### `docs/schedule.md` (MOD — documentation, static doc)

**Self-extension:** Phase 3 keeps the existing four sections and adds two:

1. A numbered "Cloud routine setup walkthrough" replacing the current shallow "Local vs. cloud" table column on the cloud side.
2. A "Run-now checklist" after the walkthrough.

**Existing "Local vs. cloud" table — analog for cloud-specific framing** (`docs/schedule.md:18-25`):

```markdown
| Concern | Local terminal | Cloud routine |
|---|---|---|
| BigQuery auth | Your `gcloud` login | Service account key in routine env vars |
| Notion access | Local MCP server | Web connector in your Anthropic account |
| Repo access | Local clone | Repo selected in the routine config |
| Environment variables | Your shell / `.env` | Per-routine config in the Anthropic UI |
```

**Correction:** the "Service account key in routine env vars" cell is now WRONG per Phase 3 D-01 (cloud routine uses BigQuery web connector, no SA key). Update this cell to: "BigQuery web connector (authorized once in your Anthropic account)". The rest of the table is correct.

**Existing reference link pattern** (`docs/schedule.md:45-48`):

```markdown
## Reference

- [Claude Code Routines (`/schedule`)](https://code.claude.com/docs/en/routines) — official docs.
- `docs/runbook.md` — what to do when a scheduled run errors.
```

Use the same `- [Title](url) — note.` shape for any new links in the walkthrough section.

**New "Cloud routine setup walkthrough" section** — no in-repo analog for numbered-UI-walkthrough docs. Apply the field-name-by-field-name pattern from RESEARCH.md "Cloud Routine Setup Walkthrough Requirements" lines 252-275. Concrete shape:

```markdown
## Cloud routine setup walkthrough

Run once when first wiring the routine. After that, edits use the same form (see "Changing the schedule" below).

1. **Authorize the BigQuery and Notion connectors once.** In your Anthropic account at https://claude.com → Settings → Connectors, verify both BigQuery (Google Cloud) and Notion are connected. If not, follow the per-connector authorization flow. The cloud routine has no `bq` or `gcloud` CLI installed; the BigQuery connector is the only data path.
2. **Open the Routines page.** claude.com → Settings → Routines → New Routine.
3. **Routine name.** `channel-patterns-analyzer-weekly`.
4. **Instructions.** Paste the full contents of `.claude/commands/run-analyzer.md` into the Instructions box. The recipe is self-contained; do not edit it after pasting (edits drift from the repo source — see `docs/maintenance.md`).
5. **Repositories.** Select `channel-patterns-analyzer`. Required: Step 4 of the recipe reads prior reports from the cloned repo.
6. **Trigger.** Select Schedule → Weekly → Monday → 9:00 AM → America/Phoenix.
7. **Connectors.** Verify BigQuery (Google Cloud) and Notion appear under Connectors. Remove any others (Slack, Linear, etc.) that are not needed.
8. **Environment variables.** Under the environment's settings, add three:
   - `NOTION_REPORT_PAGE_ID=<from your local .env>`
   - `BQ_PROJECT=<your GCP project id>`
   - `BQ_DATASET=youtube_analytics`
9. Click **Create**.
```

**New "Run-now checklist" section** — apply the table pattern from `docs/runbook.md`:

```markdown
## Run-now checklist (smoke-test before relying on the Monday schedule)

Click **Run now** on the routine's detail page. Verify within ~3 minutes:

- [ ] (a) A new child page appears under the channel-patterns parent in Notion within 60s, titled `Weekly report, {today's Phoenix date}`. (If not, see runbook § "Notion write failed" or § "BigQuery MCP connector not authorized".)
- [ ] (b) The Notion page renders all six sections: Data Health, Headline, What is working, What is not working, Patterns worth watching, Open questions. Spot-check one finding for a `(label, n=N)` parenthetical — Notion should render it as plain text (not stripped, not linkified).
- [ ] (c) The Anthropic UI shows the routine run as completed (green status). Note: green means the session exited without an infrastructure error, not that the analysis succeeded — open the run transcript and confirm no `category: ...` error lines appear.
- [ ] (d) After the cloud routine's PR merges (or you `git pull` the `claude/...` branch), `runs/{date}/summary.json` exists with `notion_write_ok: true` and an empty `errors: []` array.

If any check fails, the linked runbook section names the recovery.
```

---

### `docs/runbook.md` (MOD — documentation, failure-mode playbook)

**Analog:** existing 6 sections in the same file. Every new section follows the same template.

**Symptom / Fix / Recording template** (`docs/runbook.md:9-25`, "BigQuery auth failure" — the canonical example):

```markdown
## BigQuery auth failure

**Symptom.** `bq query` returns `Could not load the default credentials` or `Reauthentication is needed`. The analyzer's first SQL call errors out.

**Fix (local).**

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project "$BQ_PROJECT"
```

Then re-run the analyzer.

**Fix (scheduled cloud routine).** The routine doesn't have your laptop's `gcloud` login. It needs BigQuery credentials passed as environment variables (typically a service account key). Check the routine's environment config in the Anthropic UI and confirm the service account is still valid in GCP. See `docs/schedule.md` for the cloud-vs-local distinction.

**Recording.** If credentials expired on a known cadence (e.g., 90-day service-account key rotation), note the next expiry in `CHANGELOG.md` so future-you isn't surprised.
```

**Apply this shape to every new section.** Required subheadings: `**Symptom.**`, `**Fix.**` (optionally split into `**Fix (local).**` / `**Fix (cloud).**` when the recovery differs), `**Recording.**`. Section heading is `## <Failure name as the operator sees it>`.

**Bug to fix as part of any runbook edit** — the existing `## BigQuery auth failure` "Fix (scheduled cloud routine)" paragraph names "service account key" as the cloud auth method (`docs/runbook.md:23`). This is now WRONG per Phase 3 D-01. Update to:

```markdown
**Fix (scheduled cloud routine).** The routine uses the BigQuery web connector authorized in your Anthropic account, not a service account key. If the connector is the issue, see § "BigQuery MCP connector not authorized" below. The routine has no `bq` or `gcloud` CLI; do not look for missing local-auth state.
```

**New sections Phase 3 adds** (per RESEARCH.md "Failure Mode Inventory" lines 220-244). Each follows the template above:

1. `## BigQuery MCP connector not authorized` (cloud-side)
2. `## Notion connector not authorized` (cloud-side; the existing `## Notion write failed` covers local MCP)
3. `## Routine environment variable missing in cloud config` (cloud-side; existing `## Required environment variable is missing` covers local `.env`)
4. `## Routine run timed out or hung` (cloud-side)
5. `## Anthropic UI shows error before recipe runs` (cloud-side; repo clone failed, network blocked, etc.)
6. `## How to test the stale-data path without real stale data` (operator note — covers `SIMULATE_STALE` per RESEARCH.md inventory item #5)
7. `## Skill input dict missing a required key` (category `report_dict_invalid` from recipe Step 8; needs a runbook target per Phase 1 deferral noted in `01-04-SUMMARY.md:54`)
8. `## write-notion-report Skill not loaded in the session` (category `skill_unavailable` from recipe Step 9)
9. `## No BigQuery transport available` (category `no_bigquery_transport` from recipe Step 1)

**Cross-reference rot to fix** (per CONCERNS.md and Phase 1 commit `45e6054`):

The runbook used to reference `BUSINESS_RULES.md §5` and `§6`; Phase 1 Plan 01-04 fixed the runbook side to use section titles. Phase 3 should verify the same fix landed in `docs/maintenance.md:9` (which CONCERNS.md flagged still says `§6`). Replace `BUSINESS_RULES.md §6` with `BUSINESS_RULES.md § "Table grain and join keys (data contract)"`.

---

### `.env.example` (MOD — configuration)

**Self-modification:** Phase 3 removes four unused vars per CONCERNS.md "Unused environment variables" and per RESEARCH.md Open Question 6 (recommendation: REMOVE all four).

**Existing boxed-divider comment style — preserve verbatim** (`.env.example:5, 10, 21, 25, 30`):

```bash
# ─── Data source mode ───────────────────────────────────────────
# ─── Google Cloud / BigQuery ────────────────────────────────────
# ─── YouTube channel identity ───────────────────────────────────
# ─── Notion ──────────────────────────────────────────────────────
# ─── Analysis configuration ─────────────────────────────────────
```

After removal, the remaining sections collapse to three: Data source mode, Google Cloud / BigQuery, Notion. The "YouTube channel identity" section (which only held `YOUTUBE_CHANNEL_ID`) and the "Analysis configuration" section (which held `ANALYSIS_LOOKBACK_DAYS`, `MIN_VIDEO_AGE_DAYS`, `SCHEDULE_TIMEZONE`) disappear entirely.

**Final shape (target)** — four vars only:

```bash
# Channel Patterns Analyzer — environment template
# Copy this file to `.env` and fill in your own values.
# `.env` is gitignored — never commit your real values.

# ─── Data source mode ───────────────────────────────────────────
# `bigquery` (default) — analyzer queries BigQuery via the bq CLI (local) or BigQuery MCP (cloud routine)
# `csv`               — analyzer reads from ./sample_data/*.csv (demo / no-BQ-auth path)
DATA_SOURCE=bigquery

# ─── Google Cloud / BigQuery ────────────────────────────────────
# Project that holds the youtube_analytics dataset.
# The bq CLI reads this from your active gcloud config OR from this env var
# if you prefer to override per-project. Set with: gcloud config set project <id>
BQ_PROJECT=your-gcp-project-id

# Dataset name (default matches the youtube-bigquery-pipeline default).
BQ_DATASET=youtube_analytics

# ─── Notion ──────────────────────────────────────────────────────
# The Notion page where the analyzer writes the weekly report.
# Get this from the page URL: notion.so/<workspace>/<page-id> — use the page-id portion.
NOTION_REPORT_PAGE_ID=
```

---

### `CHANGELOG.md` (MOD — audit log, append-only)

**Existing entry pattern** (`CHANGELOG.md:9-19`, "2026-05-25" Phase 2 entry — the canonical example):

```markdown
## 2026-05-25

Phase 2 Plan 02-01 SQL correctness fixes (D-05). All three files pass `bq` dry-run validation against the live `youtube_analytics` dataset.

- `sql/02_top_full_length_videos.sql`: before — ...; after — .... Impact on recent reports: ....
- `sql/03_age_controlled_performance.sql`: same three changes ....
- `sql/04_data_health_check.sql`: replaced four single-quoted `CURRENT_DATE('America/Phoenix')` ....
- `.claude/commands/run-analyzer.md`: Phase 2 Plan 02-02 extends the recipe. ...
- `runs/README.md`: schema documentation extended with `prior_reports_consulted` field ....
```

**Apply this shape for every Phase 3 plan's CHANGELOG entry:**

- H2 date heading (`## 2026-05-DD`).
- One-paragraph framing sentence naming the plan and what landed.
- One bullet per file changed, with `before` / `after` and `Impact on recent reports:` (or `Forward-looking:`) clauses.
- Reference the section title in `BUSINESS_RULES.md`, never the section number (per the cross-reference rot fix).

---

## Shared Patterns

### Stdlib-only Python scripts
**Source:** `scripts/csv_fallback_loader.py` (the only existing Python file)
**Apply to:** `scripts/csv_query.py` (NEW) and the modified `scripts/csv_fallback_loader.py`

- Module docstring at top, three to ten lines, ends with a `Usage:` block.
- Imports grouped: stdlib only.
- `REPO_ROOT = Path(__file__).resolve().parent.parent` for any path resolution.
- `if __name__ == "__main__": main()` entrypoint.
- Type hints on function signatures (`def foo(snapshot: date) -> list[dict]:`).
- Print progress to stdout during long operations (`print(f"  wrote {len(rows)} rows -> {path}")`).
- No new pip dependencies (PROJECT.md "no new Python packages without explicit justification").

### Phoenix-time anchor
**Source:** `sql/02_top_full_length_videos.sql`, `sql/03_age_controlled_performance.sql`, `sql/04_data_health_check.sql` (post-Plan 02-01); CLAUDE.md preflight step `TZ=America/Phoenix date +%Y-%m-%d`
**Apply to:** every Phase 3 file that touches dates

- SQL: `CURRENT_DATE("America/Phoenix")` (double-quoted, per Plan 02-01 canonical form).
- Python: `datetime.now(ZoneInfo("America/Phoenix")).date()` (stdlib `zoneinfo`, Python 3.9+).
- Shell: `TZ=America/Phoenix date +%Y-%m-%d`.
- Never use bare `date.today()` or bare `CURRENT_DATE()` — both are the bugs Phase 3 is fixing.

### Markdown doc conventions
**Source:** `docs/runbook.md`, `docs/schedule.md`, `docs/maintenance.md`
**Apply to:** all `docs/` edits in Phase 3

- `## <Section name>` for top-level sections; `###` for sub-sections.
- Bold-then-period lead-ins: `**Symptom.**`, `**Fix.**`, `**Recording.**`.
- Code fences for shell commands with explicit `bash` language tag.
- Reference filenames as backticked relative paths from repo root (`docs/runbook.md`, `scripts/csv_fallback_loader.py`).
- Reference `BUSINESS_RULES.md` sections by title (`§ "Data health expectations"`), never by number.
- No em dashes (CLAUDE.md § "Voice").

### CHANGELOG discipline
**Source:** `docs/maintenance.md` ("Adding a new SQL query" item 6: "Add a `CHANGELOG.md` entry."); `CHANGELOG.md` existing entries
**Apply to:** every Phase 3 plan that modifies any tracked file

- Each plan ends with a CHANGELOG bullet under the plan's completion date.
- Entry names every file touched and the before/after.
- Entry calls out `Impact on recent reports:` (zero, retroactive, or forward-looking) so future-Kyle knows whether to re-read the archive.
- The CHANGELOG-as-discipline rule is part of the fix, not a follow-up — the planner should expect a CHANGELOG diff in nearly every Phase 3 plan.

### `.gitignore` awareness
**Source:** `.gitignore` (Skill negation verified per RESEARCH.md); CLAUDE.md "Persistent structure"
**Apply to:** any Phase 3 file decision about what gets committed

- `sample_data/*.csv` — gitignored; regenerated per CSV-mode run; do not check in.
- `.env` — gitignored; only `.env.example` is committed.
- `reports/` and `runs/` — committed (per CLAUDE.md "Persistent structure" + RESEARCH.md ".gitignore confirmed reports/ not ignored").
- `.planning/` — gitignored per global convention; do not reference `.planning/` paths from any cloud-routine-pasteable file (per RESEARCH.md "Cloud-Portability Audit").

---

## No Analog Found

All files Phase 3 touches have either a self-modification analog or a sibling-in-same-directory analog. None of Phase 3's work introduces a role the codebase has not seen before (no new external integrations, no new test framework, no new directory layout).

The closest thing to a no-analog item: the numbered cloud-routine UI walkthrough in `docs/schedule.md` has no existing in-repo "concrete step-by-step UI guide" precedent. The planner should pull the field names verbatim from RESEARCH.md lines 252-275 (which captured them live from claude.com/docs on 2026-05-26) and follow `docs/runbook.md`'s Symptom/Fix/Recording-adjacent tone (operator-facing, short sentences, no marketing voice).

## Metadata

**Analog search scope:** `scripts/`, `docs/`, `.claude/commands/`, `runs/2026-05-25/queries/`, `CHANGELOG.md`, `.env.example`, `BUSINESS_RULES.md`, `CLAUDE.md`.
**Files scanned:** 12 (5 reads from the upstream input plus 7 analog reads).
**Pattern extraction date:** 2026-05-25.

## PATTERN MAPPING COMPLETE
