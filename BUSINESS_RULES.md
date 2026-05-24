# Business Rules

This file contains stable domain rules that the analyzer must respect. It is imported into Claude Code via `@BUSINESS_RULES.md` from the analyzer's `CLAUDE.md`, so every session inherits these rules automatically.

These are not prompt instructions. These are facts about how analysis works in this specific context. Edit this file to update rules; do not put them in CLAUDE.md (the operating brain) directly.

---

## 1. Fiscal year start

Fiscal year starts in **July**, not January. Every quarterly or year-over-year aggregation in reports must use July as the FY anchor:

- FY2026 = July 2025 through June 2026
- Q1 FY2026 = July 2025 – September 2025
- Q2 FY2026 = October 2025 – December 2025
- Q3 FY2026 = January 2026 – March 2026
- Q4 FY2026 = April 2026 – June 2026

Calendar-year comparisons are still allowed when explicitly labeled (e.g., "CY2025 view counts"), but FY is the default.

---

## 2. Exclude internal test channels

Any video published from these test/internal channels should be excluded from analysis:

- *(no internal test channels currently — placeholder for future use)*

If a `channel_id` filter is needed, it goes here.

---

## 3. Age-control rule for cross-video comparison

When comparing videos by performance metrics (views, watch time, engagement), **always control for video age**. A video published last week has had far less time to accumulate views than one published a year ago — a direct comparison is misleading.

**Rules:**

- Any video with `days_since_published < 14` must be flagged as **low-confidence** in the report. Do not include it in "top performers" lists or "patterns" analyses by default.
- When comparing videos across a meaningful age gap (e.g., 30 days vs. 1 year), normalize to a comparable window: report "views in first 30 days" rather than "total views."
- When the analyzer reports a "trending up" or "declining" pattern, that claim must be based on at least 14 days of data per video in the comparison set.

---

## 4. Small-sample warnings

The KC Labs AI channel currently has 23 full-length videos and 105 shorts (as of 2026-05-24). Patterns drawn from small samples are unreliable.

**Rules:**

- Any pattern claim based on fewer than **5 videos** must be labeled "low-confidence (small sample)."
- Patterns based on 5–10 videos: label as "moderate confidence."
- Patterns based on 10+ videos: standard confidence.
- If a comparison group has 1–2 videos in it, do not draw a pattern conclusion. Report the raw numbers and say "too few videos to claim a pattern."

---

## 5. Data health expectations

The analyzer reads from four BigQuery tables in the `youtube_analytics` dataset:

| Table | Expected refresh | Action if stale |
|---|---|---|
| `video_metadata` | daily (snapshot_date = today or yesterday) | Flag in report's Data Health section |
| `daily_video_stats` | daily | Flag |
| `daily_video_analytics` | daily | Flag |
| `daily_traffic_sources` | daily | Flag |

If any table is more than **3 days stale** (latest snapshot_date older than `CURRENT_DATE() - 3`), the analyzer must surface this in a "Data Health" section at the top of the report, naming each stale table and how stale it is. Do not silently produce a report based on stale data.

---

## 6. Voice + tone rules

Inherited from `CLAUDE.md`, but reinforced here because they're stable:

- Be brutally honest about what underperformed. Do not soften.
- Never make a claim the data does not support.
- Calibrate confidence to sample size (per rule 4).
- KC Labs voice: humble, evidence-based, learning together with the audience — not promotional.
