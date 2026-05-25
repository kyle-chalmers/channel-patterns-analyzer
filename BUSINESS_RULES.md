# Business Rules

Stable analysis rules that the analyzer must respect. This file is imported into Claude Code via `@BUSINESS_RULES.md` from the analyzer's `CLAUDE.md`, so every session inherits these rules automatically.

These are not prompt instructions. Most are policy choices about how analysis works in this specific context — codified here so the analyzer's CLAUDE.md (the operating brain) stays focused on voice and reasoning, while the rules stay focused on consistent decisions.

---

## 1. Fiscal year start

Fiscal year starts in **July**, not January. Every quarterly or year-over-year aggregation in reports must use July as the FY anchor:

- FY2026 = July 2025 through June 2026
- Q1 FY2026 = July 2025 – September 2025
- Q2 FY2026 = October 2025 – December 2025
- Q3 FY2026 = January 2026 – March 2026
- Q4 FY2026 = April 2026 – June 2026

Calendar-year comparisons are still allowed when explicitly labeled (e.g., "CY2025 view counts"), but FY is the default.

## 2. Exclude internal test channels

Any video published from these test/internal channels should be excluded from analysis:

- *(no internal test channels currently — placeholder for future use)*

If a `channel_id` filter is needed, it goes here.

## 3. Age-control rule for cross-video comparison

When comparing videos by performance metrics (views, watch time, engagement), **always control for video age**. A video published last week has had far less time to accumulate views than one published a year ago — a direct comparison is misleading.

**Rules:**

- Any video with `days_since_published < 14` must be flagged as **low-confidence** in the report. Do not include it in "top performers" lists or "patterns" analyses by default.
- When comparing videos across a meaningful age gap (e.g., 30 days vs. 1 year), normalize to a comparable window: prefer "views in first 30 days" over "total views." If the data doesn't support a strict first-30-day window, use views-per-day-since-publish as a proxy AND label it as such in the report.
- When the analyzer reports a "trending up" or "declining" pattern, that claim must be based on at least 14 days of data per video in the comparison set.

## 4. Small-sample thresholds (query the count dynamically)

Patterns drawn from small samples are unreliable. Before applying pattern thresholds, the analyzer should query the current full-length video count from `video_metadata` (most recent snapshot) and apply the thresholds against the live count — do not hardcode it. As of the time this file was written, the channel had roughly 23 full-length videos.

**Rules:**

- Any pattern claim based on fewer than **5 videos** must be labeled "low-confidence (small sample)."
- Patterns based on 5–10 videos: label as "moderate confidence."
- Patterns based on 10+ videos: standard confidence.
- If a comparison group has 1–2 videos in it, do not draw a pattern conclusion. Report the raw numbers and say "too few videos to claim a pattern."

## 5. Data health expectations

The analyzer reads from four BigQuery tables in the `youtube_analytics` dataset:

| Table | Expected refresh | Action if stale |
|---|---|---|
| `video_metadata` | daily (snapshot_date = today or yesterday) | Flag in report's Data Health section |
| `daily_video_stats` | daily | Flag |
| `daily_video_analytics` | daily | Flag |
| `daily_traffic_sources` | daily | Flag |

If any table is more than **3 days stale** (latest `snapshot_date` older than `CURRENT_DATE() - 3` in Phoenix time / America/Phoenix), the analyzer must surface this in a "Data Health" section at the top of the report, naming each stale table and how stale it is. Do not silently produce a report based on stale data.

## 6. Table grain and join keys (data contract)

These constraints apply to every analyzer query and downstream join. Document and respect them:

| Table | Grain | Primary key |
|---|---|---|
| `video_metadata` | One row per `(video_id, snapshot_date)` | `(video_id, snapshot_date)` |
| `daily_video_stats` | One row per `(video_id, snapshot_date)` | `(video_id, snapshot_date)` |
| `daily_video_analytics` | One row per `(video_id, snapshot_date)` | `(video_id, snapshot_date)` |
| `daily_traffic_sources` | One row per `(video_id, snapshot_date, traffic_source_type)` | `(video_id, snapshot_date, traffic_source_type)` |

- Join the first three tables on `(video_id, snapshot_date)`. Never on `video_id` alone — that produces a Cartesian explosion across snapshot dates.
- `daily_traffic_sources` has multiple rows per (video_id, snapshot_date) — one per source type. Aggregate before joining or join with `SUM(views) GROUP BY video_id, snapshot_date` first.
- The "latest common snapshot" is `MIN(MAX(snapshot_date))` across all source tables. Use this when the analyzer wants the latest day where ALL tables have data — not just metadata's latest.

## 7. Voice + tone rules

Inherited from `CLAUDE.md`, but reinforced here because they're stable:

- Be brutally honest about what underperformed. Do not soften.
- Never make a claim the data does not support.
- Calibrate confidence to sample size (per rule 4).
- KC Labs voice: humble, evidence-based, learning together with the audience — not promotional.
