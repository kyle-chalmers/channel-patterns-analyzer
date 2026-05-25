# Live Build Prompts

This is the sequence of prompts that build the analyzer in the companion video. It's a standalone reference so you can follow along even if you haven't watched the video yet (and a useful checklist if you have).

Pre-auth: you should have `gcloud auth login` done and (when you get there) Notion connected per the README setup steps.

---

## Prompt 1 — Draft the analyzer's CLAUDE.md (Layer 1)

```text
Draft a CLAUDE.md file for a YouTube channel pattern analyzer. The voice should
match KC Labs — humble, evidence-based, learning together with the audience. The
analyzer should be brutally honest about what underperformed. When it compares
videos, it must account for video age, because a video published last week has
had far less time to accumulate views than one published a year ago, and a
direct comparison would be misleading. It should flag any pattern based on a
small number of videos as low-confidence. It should never make a claim the data
does not actually support.
```

**Expected output:** a CLAUDE.md with role + voice + analysis rules + small-sample handling + age-control rule + an `@BUSINESS_RULES.md` import line.

---

## Prompt 2 — Wire BigQuery (Layer 3)

```text
Help me wire Claude Code into Google BigQuery so the analyzer can query my
youtube_analytics dataset. Use the bq CLI for authentication and connection.
The four tables are video_metadata, daily_video_stats, daily_video_analytics,
daily_traffic_sources, joined on (video_id, snapshot_date), partitioned by
snapshot_date.
```

**Expected:** bq CLI configured, one successful `bq query` against `video_metadata` + `daily_video_stats` returning real channel metrics.

---

## Prompt 3 — Set up Notion both ways (Layer 3)

```text
Set up Notion access two ways. First, add the local Notion MCP server to my
Claude Code config for terminal use. Second, walk me through configuring
Notion as a Claude connector on the web for cloud routines. Then write a
quick test entry to my channel-patterns Notion page using the local MCP to
verify.
```

**Expected:** local MCP configured, web connector configured at claude.com, successful test write.

---

## Prompt 4 — Install GSD live (Layer 4 setup)

```text
Install the GSD framework globally on this machine. Walk me through what you
are doing as you do it.
```

**Expected:** install commands executed; GSD slash commands available in Claude Code.

---

## Prompt 5 — GSD plans the analyzer (Layer 4)

```text
/gsd:new-project a YouTube channel pattern analyzer. Connect to my
youtube_analytics dataset in Google BigQuery via the bq CLI. Tables:
video_metadata, daily_video_stats, daily_video_analytics, daily_traffic_sources.
Join on (video_id, snapshot_date). Run AI analysis with the system prompt in
CLAUDE.md, respecting the business rules in BUSINESS_RULES.md. Write the report
to my channel-patterns Notion page. The plan should include creating a
write-notion-report Skill that the analyzer calls — the Skill encapsulates the
Notion write logic so the analyzer just hands it a report and lets the skill
handle the rest. Also include a data-health check as the first step of the
analyzer: for each analytics table, surface the latest snapshot date and flag
any table that has not been refreshed in the last 3 days so the report always
tells me when upstream data is stale. Hedge on small samples. Respect the
DATA_SOURCE environment variable — if it is `csv`, read from ./sample_data/*.csv
instead of BigQuery (the CSV schemas match the BQ table schemas exactly).
```

**Expected:** GSD interview triggered, clarifying questions, phased plan with 4 phases (BQ + data-health, analysis, skill build, wire-up).

---

## Prompt 6 — Execute phase 1

```text
/gsd:execute phase 1.
```

**Expected:** Phase 1 implementation (BQ connection + data-health check) with file edits and a test query. **Note:** the data-health check will likely flag `daily_video_analytics` as stale — that's a real upstream issue, not an analyzer bug.

---

## Prompt 7 — Build the write-notion-report Skill on camera

```text
/gsd:execute phase 3. Specifically — create a Claude Code Skill called
write-notion-report. It should take a structured report dictionary as input
and write it to the Notion channel-patterns page using the Notion MCP. Include
clear when-to-use instructions so Claude knows to invoke it when handed a
completed analysis.
```

**Expected:** `.claude/skills/write-notion-report/SKILL.md` generated.

---

## Prompt 8 — Wire the analyzer to call the Skill

```text
/gsd:execute phase 4. Wire the analyzer to call the write-notion-report skill
when it finishes the analysis.
```

**Expected:** analyzer code updated to invoke the Skill on completion.

---

## Prompt 9 — Run the analyzer end-to-end

```text
Run the analyzer end-to-end. Pull the last 90 days of snapshots from the
youtube_analytics dataset in BigQuery, run the analysis, and have it call the
write-notion-report skill to publish.
```

**Expected:** full pipeline executes; BQ query returns rows; analysis runs; skill invoked; Notion page populated (with a Data Health warning if anything is stale).

---

## Prompt 10 — Wrap as a scheduled routine (Layer 4 — operate)

```text
Help me wrap this analyzer as a Claude Code routine that runs every Monday at
9am Phoenix time using /schedule. The routine should run the analyzer
end-to-end — query the youtube_analytics dataset in BigQuery, run analysis,
call the write-notion-report skill, write to my channel-patterns Notion page.
```

**Expected:** routine config generated, scoped to repo + env vars + Notion web connector + BQ service-account credentials. **Verify in the Anthropic web UI before firing** — see the "Scheduling: cloud setup ≠ local setup" section of the README.

---

## Action step — Fire the routine

In Anthropic's web UI at [claude.com](https://claude.com), click **Run now** on the routine. The analyzer will execute end-to-end and the Notion page should update.
