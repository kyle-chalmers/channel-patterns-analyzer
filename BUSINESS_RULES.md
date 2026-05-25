# Business Rules

Stable domain facts and data-contract rules that the analyzer must respect. This file is imported into the analyzer's `CLAUDE.md` via `@BUSINESS_RULES.md`, so every session inherits these automatically.

The analyzer's voice, reasoning rules, age-control mechanics, sample-size thresholds, and report structure live in `CLAUDE.md`. This file is reserved for facts that outlive any session — the fiscal calendar, exclusions, the data refresh contract, and the per-table grain.

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

## 3. Data health expectations

The analyzer reads from four BigQuery tables in the `youtube_analytics` dataset:

| Table | Expected refresh | Action if stale |
|---|---|---|
| `video_metadata` | daily (snapshot_date = today or yesterday) | Flag in report's Data Health section |
| `daily_video_stats` | daily | Flag |
| `daily_video_analytics` | daily | Flag |
| `daily_traffic_sources` | daily | Flag |

If any table is more than **3 days stale** (latest `snapshot_date` older than `CURRENT_DATE() - 3` in Phoenix time / America/Phoenix), the analyzer must surface this in a "Data Health" section at the top of the report, naming each stale table and how stale it is. Do not silently produce a report based on stale data.

## 4. Table grain and join keys (data contract)

These constraints apply to every analyzer query and downstream join. Document and respect them:

| Table | Grain | Primary key |
|---|---|---|
| `video_metadata` | One row per `(video_id, snapshot_date)` | `(video_id, snapshot_date)` |
| `daily_video_stats` | One row per `(video_id, snapshot_date)` | `(video_id, snapshot_date)` |
| `daily_video_analytics` | One row per `(video_id, snapshot_date)` | `(video_id, snapshot_date)` |
| `daily_traffic_sources` | One row per `(video_id, snapshot_date, traffic_source_type)` | `(video_id, snapshot_date, traffic_source_type)` |

- Join the first three tables on `(video_id, snapshot_date)`. Never on `video_id` alone — that produces a Cartesian explosion across snapshot dates.
- `daily_traffic_sources` has multiple rows per `(video_id, snapshot_date)` — one per source type. Aggregate before joining or join with `SUM(views) GROUP BY video_id, snapshot_date` first.
- The "latest common snapshot" is `MIN(MAX(snapshot_date))` across all source tables. Use this when the analyzer wants the latest day where ALL tables have data — not just metadata's latest.
