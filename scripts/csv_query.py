"""CSV-mode equivalent of `bq query --format=json` for the analyzer's three live queries.

Reads `sample_data/*.csv` and emits a JSON array to stdout in the same shape
`bq query --format=json` produces: top-level array, all values JSON-string-coerced,
column names matching the SQL aliases. Mirrors:
  - sql/04_data_health_check.sql            -> data_health
  - sql/02_top_full_length_videos.sql       -> top_full_length_videos
  - .claude/commands/run-analyzer.md Step 5 -> eligible_video_count (inline SQL)

All "today" arithmetic uses ZoneInfo("America/Phoenix"), the canonical analyzer
timezone (BUSINESS_RULES.md, section "Data health expectations"). Stdlib only.

Usage:
    python scripts/csv_query.py data_health
    python scripts/csv_query.py top_full_length_videos
    python scripts/csv_query.py eligible_video_count
"""

import argparse
import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO_ROOT / "sample_data"

PHOENIX = ZoneInfo("America/Phoenix")

DATA_HEALTH_TABLES = (
    "video_metadata",
    "daily_video_stats",
    "daily_video_analytics",
    "daily_traffic_sources",
)


def _read_csv(table_name: str, sample_dir: Path = SAMPLE_DIR) -> list[dict]:
    """Read a sample CSV. csv.DictReader yields strings, which matches our JSON output."""
    path = sample_dir / f"{table_name}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"sample CSV not found: {path}. Run scripts/csv_fallback_loader.py first."
        )
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _today_phoenix() -> date:
    """Phoenix-local 'today'. Equivalent of BigQuery CURRENT_DATE('America/Phoenix')."""
    return datetime.now(PHOENIX).date()


def _parse_snapshot_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_published_at(value: str) -> date:
    """Parse a tz-aware ISO-8601 published_at into a local date. The CSV loader
    writes published_at with a `-07:00` offset (Phoenix-tz-aware), so calling
    .date() yields the local date, matching SQL `DATE(published_at, 'America/Phoenix')`.
    """
    return datetime.fromisoformat(value).date()


def _max_snapshot(rows: list[dict]) -> date | None:
    if not rows:
        return None
    return max(_parse_snapshot_date(r["snapshot_date"]) for r in rows)


def query_data_health(sample_dir: Path = SAMPLE_DIR) -> list[dict]:
    """Mirror of sql/04_data_health_check.sql. Per table, report MAX(snapshot_date)
    and days_stale against Phoenix-local today. Sorted by days_stale DESC. Empty
    tables surface as empty-string latest_snapshot and days_stale; the recipe's
    data-health step is the primary empty-table STOP.
    """
    today = _today_phoenix()
    out: list[dict] = []
    for table in DATA_HEALTH_TABLES:
        rows = _read_csv(table, sample_dir)
        latest = _max_snapshot(rows)
        if latest is None:
            out.append({"table_name": table, "latest_snapshot": "", "days_stale": ""})
        else:
            out.append({
                "table_name": table,
                "latest_snapshot": latest.isoformat(),
                "days_stale": str((today - latest).days),
            })

    def _sort_key(d: dict) -> int:
        v = d["days_stale"]
        return int(v) if v else -1

    out.sort(key=_sort_key, reverse=True)
    return out


def query_top_full_length_videos(sample_dir: Path = SAMPLE_DIR) -> list[dict]:
    """Mirror of sql/02_top_full_length_videos.sql. Joins video_metadata and
    daily_video_stats on (video_id, snapshot_date) per BUSINESS_RULES.md, section
    "Table grain and join keys (data contract)". Implementation filters both
    tables to latest_common first, then joins on video_id. Returns [] when
    either source is empty (mirrors the SQL's IS NOT NULL guard).
    """
    today = _today_phoenix()
    metadata = _read_csv("video_metadata", sample_dir)
    stats = _read_csv("daily_video_stats", sample_dir)

    max_meta = _max_snapshot(metadata)
    max_stats = _max_snapshot(stats)
    if max_meta is None or max_stats is None:
        return []
    latest_common_str = min(max_meta, max_stats).isoformat()

    metadata_filtered = [
        r for r in metadata
        if r["snapshot_date"] == latest_common_str and r["video_type"] == "full_length"
    ]
    stats_by_vid = {
        r["video_id"]: r for r in stats if r["snapshot_date"] == latest_common_str
    }

    out: list[dict] = []
    for m in metadata_filtered:
        s = stats_by_vid.get(m["video_id"])
        if s is None:
            continue
        days_since_published = (today - _parse_published_at(m["published_at"])).days
        out.append({
            "title": m["title"],
            "video_type": m["video_type"],
            "duration_formatted": m["duration_formatted"],
            "published_at": m["published_at"],
            "days_since_published": str(days_since_published),
            "view_count": s["view_count"],
            "like_count": s["like_count"],
            "comment_count": s["comment_count"],
        })

    out.sort(key=lambda d: int(d["view_count"]), reverse=True)
    return out


def query_eligible_video_count(sample_dir: Path = SAMPLE_DIR) -> list[dict]:
    """Mirror of the inline SQL in .claude/commands/run-analyzer.md Step 5. One-row
    result with keys eligible_count, total_full_length, latest_common_snapshot.
    NULL-guard: empty source tables yield zeros and an empty
    latest_common_snapshot (mirrors the SQL IS NOT NULL short-circuit).
    """
    today = _today_phoenix()
    metadata = _read_csv("video_metadata", sample_dir)
    stats = _read_csv("daily_video_stats", sample_dir)

    max_meta = _max_snapshot(metadata)
    max_stats = _max_snapshot(stats)
    if max_meta is None or max_stats is None:
        return [{
            "eligible_count": "0",
            "total_full_length": "0",
            "latest_common_snapshot": "",
        }]
    latest_common_str = min(max_meta, max_stats).isoformat()

    total_full_length_rows = [
        r for r in metadata
        if r["snapshot_date"] == latest_common_str and r["video_type"] == "full_length"
    ]
    eligible_count = sum(
        1 for r in total_full_length_rows
        if (today - _parse_published_at(r["published_at"])).days >= 14
    )
    return [{
        "eligible_count": str(eligible_count),
        "total_full_length": str(len(total_full_length_rows)),
        "latest_common_snapshot": latest_common_str,
    }]


QUERY_DISPATCH = {
    "data_health": query_data_health,
    "top_full_length_videos": query_top_full_length_videos,
    "eligible_video_count": query_eligible_video_count,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one CSV-mode query and emit a JSON array to stdout (bq --format=json shape).",
    )
    parser.add_argument("query_name", choices=sorted(QUERY_DISPATCH.keys()), help="Which query to run.")
    parser.add_argument(
        "--sample-dir", type=Path, default=SAMPLE_DIR,
        help="Override sample_data/ (developer escape hatch; CSV mode does not honor BQ_DATASET).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = QUERY_DISPATCH[args.query_name](sample_dir=args.sample_dir)
    json.dump(rows, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
