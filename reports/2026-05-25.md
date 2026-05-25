# Weekly report, 2026-05-25

## Data Health

| Table | Latest snapshot | Days stale |
|---|---|---|
| video_metadata | 2026-05-25 | 0 |
| daily_video_stats | 2026-05-25 | 0 |
| daily_video_analytics | 2026-05-25 | 0 |
| daily_traffic_sources | 2026-05-25 | 0 |

All four tables are within the 3-day freshness contract from BUSINESS_RULES.md §3. The 89-day gap the project notes flagged on 2026-05-24 for `daily_video_analytics` and `daily_traffic_sources` has resolved; the upstream pipeline is current.

## Headline

The full-length back catalog is carrying the channel. The top video, "Claude Code vs Manual Jira Ticket Work," sits at 10,271 views after 199 days. Phase 1 ships only this one finding plus Data Health; the comparative and pattern work lands in Phase 2.

## What is working

**Top full-length video: "Claude Code vs Manual Jira Ticket Work | The Difference Is Amazing"**. 10,271 views, 199 days since published.

This is a raw top-N reading, not a pattern claim. Confidence: low. One video at the top of the cumulative-views chart only tells us it is the most-watched full-length video. It does not tell us what is making it work, whether the win is repeatable, or how it is performing against age-normalized peers. Phase 2 wires the age-normalized comparison.

## What is not working

Not analyzed in this run. Phase 2 wires the underperformance analysis (age-normalized comparisons against the channel median).

## Patterns worth watching

Not analyzed in this run. Phase 2 wires pattern detection (titles, thumbnails, topic clusters) with explicit confidence labels per CLAUDE.md §"Small samples get hedged".

## Open questions

Not recorded this run. Phase 2 surfaces hypotheses the data hints at but cannot answer.
