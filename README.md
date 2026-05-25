# Channel Patterns Analyzer

A scheduled Claude Code analyzer that reads YouTube channel metrics from BigQuery, identifies what's actually working on the channel (controlled for video age and small samples), and publishes a weekly report to Notion.

**Built live as part of:** [The 4 Layers of Context Engineering (Make AI Actually Useful)](https://www.youtube.com/@kylechalmersdataai) — a KC Labs AI video that teaches the 4-layer Context Engineering framework (Instructions, Structure, Tools, Workflows) through one sustained build.

This repo is the companion to the video. Watching is not required — the README is self-contained.

---

## Which layer is your bottleneck?

Before you read further, here's a quick self-diagnostic. If AI keeps failing you in one of these ways, that's the layer to invest in first.

![Decision tree: which layer is your bottleneck?](./images/diagram-decision-tree.png)

This repo demonstrates all four layers in one sustained build. Pick a layer you're stuck on and read its section first.

---

## The 4 layers, embodied

Every file in this repo is an exhibit of one of the four layers:

| Layer | What it is in this repo |
|---|---|
| **1. Instructions** | `CLAUDE.md` — the analyzer's operating brain (voice, rules, hedging guidance). Committed as the reference version; viewers who run Prompt 1 will draft their own and overwrite it. |
| **2. Structure** | `BUSINESS_RULES.md` (imported from CLAUDE.md via `@BUSINESS_RULES.md`) + folder layout (`sql/`, `scripts/`, `images/`) |
| **3. Tools** | BigQuery (`bq` CLI) for the data source; Notion (local MCP for terminal sessions + Claude web connector for cloud routines) for the output destination |
| **4. Workflows** | The build pattern (GSD-driven planning, AI as doer + Kyle as project manager) + a Claude Code Skill (`write-notion-report`) + a scheduled `/schedule` routine that runs the analyzer every Monday at 9am Phoenix time + a persistent `reports/` archive and `runs/` audit trail so each weekly run leaves a durable record (see [Persistent structure](#persistent-structure)) |

Without all four, this would be a chatbot. With all four, it runs without me.

---

## Architecture

![4-layer Context Engineering — channel patterns analyzer overlay](./images/diagram.png)

Data flow:

```
┌──────────────────────────────────┐
│       Claude Code Routine        │
│   (/schedule, weekly @ Monday)   │
└────────────────┬─────────────────┘
                 │
                 ▼
   ┌─────────────────────────┐
   │  Analyzer (this repo)   │
   │  • CLAUDE.md → voice    │
   │  • BUSINESS_RULES.md    │
   │  • bq CLI → BigQuery    │
   └────┬────────────────┬───┘
        │                │
        ▼                ▼
┌──────────────┐  ┌──────────────────┐
│   BigQuery   │  │  write-notion-   │
│ youtube_     │  │  report Skill    │
│ analytics    │  │  → Notion page   │
│ (4 tables)   │  │                  │
└──────────────┘  └──────────────────┘
```

---

## Prerequisites

| Tool / service | Purpose | Setup |
|---|---|---|
| **Claude Code** | The AI agent that runs the analyzer | [claude.ai/download](https://claude.ai/download) |
| **Google Cloud + BigQuery** | Data source | Need an existing `youtube_analytics`-style dataset. If you don't have one, the [youtube-bigquery-pipeline](https://github.com/kyle-chalmers/youtube-bigquery-pipeline) repo builds it for you. Free tier covers it. |
| **`gcloud` CLI** | Authentication | `gcloud auth login` then `gcloud config set project <your-project>` |
| **`bq` CLI** | Querying BigQuery | Comes with the Google Cloud SDK |
| **Notion account** | Output destination | Free tier fine for a single page |
| **Notion MCP** (terminal use) | Local Claude Code → Notion | See [notion.com/integrations](https://www.notion.com/integrations) |
| **Notion Claude connector** (cloud routines) | Scheduled runs → Notion | Configure in your [Anthropic account](https://claude.com) under Connectors |
| **GSD framework** (optional) | Workflow scaffolding for the build | `claude` then ask it to install GSD |

**No BigQuery yet?** See the [CSV fallback](#csv-fallback-for-non-bigquery-users) section below — you can follow along with a sample dataset.

---

## Setup

### 1. Clone and configure

```bash
git clone https://github.com/kyle-chalmers/channel-patterns-analyzer.git
cd channel-patterns-analyzer
cp .env.example .env
# Edit .env: set BQ_PROJECT, BQ_DATASET, NOTION_REPORT_PAGE_ID, and DATA_SOURCE
```

### 2. Install Python dependencies (only needed for the CSV fallback path)

```bash
pip install -r requirements.txt
```

### 3. Wire up BigQuery from scratch

If you've never used the Google Cloud SDK on this machine, do the full walkthrough below. If `gcloud` and `bq` are already installed and authenticated, skip to step 3.5 (smoke test).

The SQL files in `sql/` reference the dataset by its bare name (`youtube_analytics.video_metadata` etc.) because the **project** comes from your active gcloud config, not from the SQL.

#### 3.1 Install the Google Cloud SDK (ships with `gcloud` and `bq`)

macOS (Homebrew):

```bash
brew install --cask google-cloud-sdk
```

Other platforms or a manual install: follow [cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install).

Verify both CLIs are on your PATH:

```bash
gcloud --version
bq version
```

If `bq` is missing after a fresh install, install the bundled component explicitly:

```bash
gcloud components install bq
```

#### 3.2 Authenticate (two separate logins)

```bash
# 1. User credentials — what `gcloud` and `bq` use for interactive commands.
gcloud auth login

# 2. Application Default Credentials — what client libraries (Python, etc.) use.
#    Needed if you ever query BigQuery from a script instead of the bq CLI.
gcloud auth application-default login
```

Both commands open a browser. Sign in with the Google account that has access to the project holding `youtube_analytics`.

#### 3.3 Point gcloud at your project

Load `BQ_PROJECT` and `BQ_DATASET` from `.env` and set the project as the active gcloud project:

```bash
# Pull BQ_PROJECT and BQ_DATASET into your shell from .env
export $(grep -E '^(BQ_PROJECT|BQ_DATASET)=' .env | xargs)

gcloud config set project "$BQ_PROJECT"
gcloud config list   # confirm: account = your email, project = $BQ_PROJECT
```

`BQ_DATASET` will almost certainly be something other than `youtube_analytics` — that's just the placeholder name from the [youtube-bigquery-pipeline](https://github.com/kyle-chalmers/youtube-bigquery-pipeline) repo. Set it to whatever your dataset is actually called in BigQuery. Run `bq ls` (next step) to confirm the name.

#### 3.4 Enable the BigQuery API (one-time per project)

```bash
gcloud services enable bigquery.googleapis.com
```

If the project already had BigQuery enabled, this is a no-op and exits cleanly.

#### 3.5 Smoke-test access

First, see what datasets actually live in the project so you can set `BQ_DATASET` correctly:

```bash
bq ls   # lists every dataset in $BQ_PROJECT — pick the one holding your YouTube tables
```

If the name doesn't match what's in `.env`, update `.env` now and re-run `export $(grep -E '^(BQ_PROJECT|BQ_DATASET)=' .env | xargs)`.

Then confirm the four expected tables are in the dataset and inspect one:

```bash
bq ls "$BQ_DATASET"                  # should list 4 tables: video_metadata, daily_video_stats, daily_video_analytics, daily_traffic_sources
bq show "$BQ_DATASET.video_metadata"
```

Run a tiny query against the freshest snapshot to confirm read access end-to-end:

```bash
bq query --use_legacy_sql=false --format=pretty \
  "SELECT COUNT(*) AS rows_today
   FROM \`$BQ_DATASET.video_metadata\`
   WHERE snapshot_date = CURRENT_DATE('America/Phoenix')"
```

If that returns a row count, the analyzer can read BigQuery. If it errors, the most common causes are:

- **403 / permission denied:** the signed-in user doesn't have `roles/bigquery.dataViewer` on the dataset (or `roles/bigquery.jobUser` on the project). Grant in the GCP console under IAM.
- **404 / not found:** `BQ_DATASET` doesn't match what's actually in BigQuery. Run `bq ls` again, update `.env`, and re-export.
- **`bq: command not found`:** the SDK installed but `bq` isn't on PATH. Re-run `gcloud components install bq` or restart your shell.

#### 3.6 Dataset name in the SQL files

The SQL files in `sql/` currently hardcode `youtube_analytics.<table>`. Your dataset is almost certainly named something else, so either:

- One-line find-and-replace `youtube_analytics` → `$BQ_DATASET` (your real name) across `sql/*.sql`, or
- Have the analyzer template the dataset name from `$BQ_DATASET` at query time (this is the preferred pattern — it keeps the SQL files portable and matches what `CLAUDE.md` already instructs).

### 4. Configure Notion — both ways

The video demos two paths because cloud routines and terminal sessions see different surfaces:

- **Local MCP** (terminal sessions): your local Claude Code talks to Notion via an MCP server. The exact install command depends on the current Notion MCP distribution (check [notion.com/integrations](https://www.notion.com/integrations) — at recording time, verify with `claude mcp add notion <official-url-or-npx-cmd>` against current docs).
- **Web connector** (scheduled routines): in your Anthropic account at [claude.com](https://claude.com), go to Connectors → add Notion. Cloud routines see this; they do NOT see your local MCP config.

### 5. Configure the BigQuery MCP connector (for Claude.ai web / cloud routines)

The `bq` CLI from Step 3 is what your **local** Claude Code session uses. Scheduled routines and Claude.ai web sessions run in a different environment that does NOT see your local `gcloud` login — they need their own connector. This step wires that up.

If you only ever run the analyzer locally from your terminal, you can skip this step.

#### 5.1 Create OAuth credentials in Google Cloud

In [console.cloud.google.com](https://console.cloud.google.com/), with the same project that holds `$BQ_DATASET`:

1. **APIs & Services → OAuth consent screen** — if you've never configured this for the project, do it now. User type **External** (unless you're on Google Workspace and want Internal). Fill in app name + your email. For scopes, add `https://www.googleapis.com/auth/bigquery.readonly` (read-only is enough — the analyzer never writes). Add your own email as a test user.

2. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - Application type: **Web application** (this matters — see the note below)
   - Name: `Claude BigQuery MCP` (or whatever you like)
   - Under **Authorized redirect URIs**, click **Add URI** and paste exactly:

     ```
     https://claude.ai/api/mcp/auth_callback
     ```

     Character-for-character. No trailing slash. This is the URL Claude redirects back to after Google signs you in.

   - Click **Create**.

3. The modal shows your **Client ID** and **Client Secret**. Keep this tab open — you'll paste both into Claude in the next step. You can also download the JSON for safekeeping.

> **Why "Web application" and not "Desktop app"?** The first time I tried this I chose Desktop and got `Error 400: redirect_uri_mismatch` at the Google sign-in screen. Desktop clients use a loopback/localhost flow and don't accept the `https://claude.ai/api/mcp/auth_callback` redirect that Claude's MCP installer uses. Web application is the correct choice.

#### 5.2 Install the connector in Claude

In Claude (the web app at [claude.ai](https://claude.ai/), or the desktop app's Connectors panel), install the Google Cloud BigQuery connector. When the install dialog asks for credentials, paste:

- **OAuth Client ID** — from Step 5.1
- **OAuth Client Secret** — from Step 5.1

Click **Continue**, then sign in with the Google account that has access to `$BQ_PROJECT`. After approval you should be redirected back to Claude with the connector installed.

**Treat the Client Secret like a password.** Don't commit it to this (public) repo — Claude stores it on its side; you don't need it locally.

### 6. Scheduling: cloud setup ≠ local setup

If you're running the analyzer locally, the steps above are enough. If you want to wrap it as a scheduled routine, the cloud environment is its own thing:

- Routines run on Anthropic's infrastructure, not your laptop.
- They need: the repo selected, environment variables defined per-routine, the Notion Claude connector (web), and BigQuery credentials that work without your local `gcloud` login (e.g., a service account key passed via env var).
- See the [Anthropic routines docs](https://code.claude.com/docs/en/routines) for the cloud-env configuration screen.

A routine that "works locally" will fail in the cloud if any of the above isn't scoped. Verify in the Anthropic UI before the routine's first scheduled fire.

### 7. (Optional) Install GSD to follow the video's build flow

```bash
claude
> "Install the GSD framework globally on this machine. Walk me through what you are doing as you do it."
```

---

## Demo prompt

The whole analyzer is built via a sequence of prompts inside Claude Code with GSD. The full prompt list is in the companion video (link in the description after the video publishes).

Quick start (Prompt 5 in the video):

```text
/gsd:new-project a YouTube channel pattern analyzer. Connect to my youtube_analytics
dataset in Google BigQuery via the bq CLI. Tables: video_metadata, daily_video_stats,
daily_video_analytics, daily_traffic_sources. Join on (video_id, snapshot_date).
Run AI analysis with the system prompt in CLAUDE.md, respecting the business rules
in BUSINESS_RULES.md. Write the report to my channel-patterns Notion page. The plan
should include creating a write-notion-report Skill that the analyzer calls — the
Skill encapsulates the Notion write logic so the analyzer just hands it a report
and lets the skill handle the rest. Also include a data-health check as the first
step of the analyzer: for each analytics table, surface the latest snapshot date
and flag any table that has not been refreshed in the last 3 days so the report
always tells me when upstream data is stale. Hedge on small samples.
```

GSD will interview you, plan the build in 4 phases, and execute each phase as you confirm.

---

## CSV fallback for non-BigQuery users

If you don't have a BigQuery dataset set up, the `scripts/csv_fallback_loader.py` script generates a sample dataset that mimics the `youtube_analytics` schema. The analyzer can read from CSV files instead of BigQuery — useful for following along without setting up the full data pipeline.

```bash
python scripts/csv_fallback_loader.py
```

This creates `sample_data/` with the same schema as the BigQuery tables, sized to be representative without being huge.

To make the analyzer use CSVs instead of BigQuery, set `DATA_SOURCE=csv` in your `.env` AND, when you're prompting GSD to build the analyzer, add:

> "Respect the DATA_SOURCE environment variable. If it is `csv`, read from `./sample_data/*.csv` instead of querying BigQuery. The CSV schemas match the BQ table schemas exactly. If it is `bigquery` (or unset), query BigQuery as normal."

The analyzer will then take both paths in its planning + execution.

---

## Repo layout

```
channel-patterns-analyzer/
├── README.md                    ← you are here
├── LICENSE                      ← MIT
├── BUSINESS_RULES.md            ← Layer 2 — stable analysis rules (imported from CLAUDE.md via @)
├── PROMPTS.md                   ← the 10 prompts that build the analyzer (follow along here)
├── CLAUDE.md                    ← Layer 1 — analyzer voice + reasoning rules (the reference draft from Prompt 1)
├── CHANGELOG.md                 ← material changes to rules, queries, or behavior (one line per change)
├── .env.example                 ← config template
├── .gitignore
├── requirements.txt
│
├── .internal/                   ← gitignored — Kyle's personal config + recording notes
│
├── sql/                         ← sample BigQuery queries (read-only patterns the analyzer uses)
│   ├── 01_latest_snapshot_overview.sql
│   ├── 02_top_full_length_videos.sql
│   ├── 03_age_controlled_performance.sql
│   └── 04_data_health_check.sql
│
├── scripts/                     ← utility scripts
│   └── csv_fallback_loader.py   ← generate sample data for non-BQ users
│
├── reports/                     ← Layer 4 persistence — weekly markdown reports, one per run date
├── runs/                        ← Layer 4 persistence — per-run audit trail (snapshot dates, query results, errors)
├── docs/                        ← operator manual — runbook, maintenance, schedule
│
├── images/
│   ├── diagram.excalidraw       ← 4-layer Context Engineering (architecture)
│   ├── diagram.png              ← rendered + KC Labs branded
│   ├── diagram-decision-tree.excalidraw  ← which layer is your bottleneck?
│   └── diagram-decision-tree.png
│
└── (gitignored — built during the video, not committed)
    ├── .claude/skills/write-notion-report/SKILL.md   ← the Skill built on camera
    ├── routine_config.json      ← /schedule routine config
    └── sample_data/             ← generated CSV fallback data
```

---

## Persistent structure

Each weekly run leaves a durable record on disk, not just in Notion. Three folders + a changelog make the analyzer sustainably maintainable — and let viewers of this repo see the analyzer's actual output history over time.

```
reports/{YYYY-MM-DD}.md         ← the weekly report, same content sent to Notion
runs/{YYYY-MM-DD}/
    summary.json                ← snapshot dates, video count, query row counts, errors
    queries/*.json              ← raw SQL results (small enough to commit)
    report.md                   ← mirror of the report, kept here so the run folder is self-contained
docs/runbook.md                 ← what to do when something breaks
docs/maintenance.md             ← how to add a query, evolve a rule, retire a pattern
docs/schedule.md                ← how the weekly /schedule routine fires
CHANGELOG.md                    ← log of material changes to rules/queries/behavior
```

The analyzer reads recent `reports/` entries to calibrate confidence over time without breaking the standalone-tone rule. The `runs/` audit trail is what makes a surprising report answerable months later. The `docs/` folder is the operator manual that keeps the repo runnable when nobody's touched it in three months.

See `reports/README.md`, `runs/README.md`, and `docs/README.md` for details.

After the video, fork this repo and run through the prompts yourself — you'll generate your own versions of all four live-built artifacts.

---

## Related KC Labs AI resources

- **AZ Tech Week Workshop materials** (the foundation this video builds on) — [data-ai-tickets-template/videos/az_tech_week_workshop](https://github.com/kyle-chalmers/data-ai-tickets-template/tree/main/videos/az_tech_week_workshop). Includes the fillable Context Engineering playbook template + starter CLAUDE.md template + curated resource guide.
- **YouTube BigQuery Pipeline** (the data source) — [github.com/kyle-chalmers/youtube-bigquery-pipeline](https://github.com/kyle-chalmers/youtube-bigquery-pipeline). Builds the `youtube_analytics` dataset this analyzer reads from.
- **KC Labs AI YouTube channel** — [youtube.com/@kylechalmersdataai](https://www.youtube.com/@kylechalmersdataai)

---

## Authoritative reading on Context Engineering

- Anthropic, [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Andrej Karpathy, [on context engineering](https://x.com/karpathy/status/1937902205765607626)
- Simon Willison, [Context engineering](https://simonwillison.net/2025/jun/27/context-engineering/)
- Drew Breunig, [How Long Contexts Fail](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html) — the four failure modes
- Dex Horthy (HumanLayer), [Advanced Context Engineering for Coding Agents](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents)
- Kyle Mistele (HumanLayer), [Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)

## Claude Code features used

- [CLAUDE.md and the `@` import syntax](https://code.claude.com/docs/en/memory)
- [Claude Code Skills](https://code.claude.com/docs/en/agents-and-tools/agent-skills/)
- [Claude Code Routines (`/schedule`)](https://code.claude.com/docs/en/routines) — shipped April 14, 2026

---

## License

MIT — see [LICENSE](./LICENSE). Fork it, adapt it, ship your own version.

---

*Made with Claude Code.*
