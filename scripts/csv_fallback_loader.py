"""Generate a sample CSV dataset that mimics the youtube_analytics BigQuery schema.

Useful for following along with the analyzer without setting up the full
youtube-bigquery-pipeline. Output goes to sample_data/ and matches the schema
of the four BigQuery tables (video_metadata, daily_video_stats,
daily_video_analytics, daily_traffic_sources).

Usage:
    python scripts/csv_fallback_loader.py
"""

import argparse
import csv
import os
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO_ROOT / "sample_data"

SAMPLE_VIDEOS = [
    # (video_id, title, duration_seconds, video_type, published_days_ago)
    ("VID001", "Claude Code vs Manual Jira Ticket Work | The Difference Is Amazing", 1610, "full_length", 28),
    ("VID002", "Claude Code Makes Databricks Easy: Jobs, Notebooks, SQL & Unity Catalog", 1082, "full_length", 45),
    ("VID003", "Claude Code + Snowflake: The Productivity Game-Changer", 2369, "full_length", 67),
    ("VID004", "Claude Code Built This Azure Pipeline in Minutes", 2455, "full_length", 88),
    ("VID005", "Claude Code Just Got Smarter for dbt Projects", 1454, "full_length", 73),
    ("VID006", "I Let Claude Code Build My Entire YouTube Analytics Pipeline", 1872, "full_length", 95),
    ("VID007", "Semantic Layers — The Skill Data Professionals Need Next", 1520, "full_length", 60),
    ("VID008", "From Zero to AI Data Analyst in One Video", 2566, "full_length", 66),
    ("VID009", "Get Set Up with AI Coding Tools in Under 10 Minutes", 545, "full_length", 54),
    ("VID010", "What Is Data Analytics in the Age of AI?", 1830, "full_length", 47),
    ("VID011", "20a: What Happens to Your Data When You Use AI", 1800, "full_length", 16),
    ("VID012", "20b: How to Safely Connect AI to Your Company Data", 2400, "full_length", 6),
    # A young video to test the age-control rule (BUSINESS_RULES.md §3)
    ("VID013", "Brand New Video (should be flagged as low-confidence)", 1200, "full_length", 3),
    # A handful of shorts (analyzer treats these separately)
    ("VID201", "Claude Code Tip #1", 45, "short", 30),
    ("VID202", "Claude Code Tip #2", 38, "short", 25),
    ("VID203", "Claude Code Tip #3", 52, "short", 20),
]


def _format_duration(seconds: int) -> str:
    minutes, sec = divmod(seconds, 60)
    return f"{minutes}:{sec:02d}"


def generate_video_metadata(snapshot: date) -> list[dict]:
    rows: list[dict] = []
    phoenix = ZoneInfo("America/Phoenix")
    snapshot_midnight = datetime.combine(snapshot, datetime.min.time(), tzinfo=phoenix)
    for vid, title, dur, vtype, days_ago in SAMPLE_VIDEOS:
        published_at = snapshot_midnight - timedelta(days=days_ago)
        rows.append({
            "video_id": vid,
            "title": title,
            "published_at": published_at.isoformat(),
            "duration_seconds": dur,
            "duration_formatted": _format_duration(dur),
            "video_type": vtype,
            "tags": "",
            "category_id": "27",
            "thumbnail_url": f"https://example.com/thumbs/{vid}.jpg",
            "snapshot_date": snapshot.isoformat(),
        })
    return rows


def generate_daily_video_stats(snapshot: date) -> list[dict]:
    rows: list[dict] = []
    rng = random.Random(42)
    for vid, _, _, vtype, days_ago in SAMPLE_VIDEOS:
        if vtype == "full_length":
            base_views = max(50, days_ago * rng.randint(20, 150))
        else:
            base_views = max(10, days_ago * rng.randint(5, 40))
        rows.append({
            "snapshot_date": snapshot.isoformat(),
            "video_id": vid,
            "view_count": base_views,
            "like_count": int(base_views * rng.uniform(0.005, 0.025)),
            "comment_count": int(base_views * rng.uniform(0.0005, 0.005)),
            "favorite_count": 0,
        })
    return rows


def generate_daily_video_analytics(snapshot: date) -> list[dict]:
    """Note: in the real pipeline this is currently stale; sample data is healthy."""
    rows: list[dict] = []
    rng = random.Random(43)
    for vid, _, dur, vtype, _ in SAMPLE_VIDEOS:
        if vtype != "full_length":
            continue
        watch_min = round(rng.uniform(50, 800), 2)
        avg_view_sec = round(rng.uniform(60, dur * 0.55), 2)
        avg_view_pct = round((avg_view_sec / dur) * 100, 2)
        rows.append({
            "snapshot_date": snapshot.isoformat(),
            "video_id": vid,
            "estimated_minutes_watched": watch_min,
            "average_view_duration_seconds": avg_view_sec,
            "average_view_percentage": avg_view_pct,
            "impressions": rng.randint(1000, 50000),
            "impression_ctr": round(rng.uniform(0.02, 0.08), 4),
            "subscribers_gained": rng.randint(0, 30),
            "subscribers_lost": rng.randint(0, 5),
            "shares": rng.randint(0, 15),
            "annotation_click_through_rate": None,
            "card_click_rate": None,
        })
    return rows


def generate_daily_traffic_sources(snapshot: date) -> list[dict]:
    rows: list[dict] = []
    sources = ["YT_SEARCH", "YT_OTHER_PAGE", "EXT_URL", "SUGGESTED_VIDEO", "BROWSE"]
    rng = random.Random(44)
    for vid, _, _, vtype, _ in SAMPLE_VIDEOS:
        if vtype != "full_length":
            continue
        for src in sources:
            views = rng.randint(5, 500)
            rows.append({
                "snapshot_date": snapshot.isoformat(),
                "video_id": vid,
                "traffic_source_type": src,
                "views": views,
                "estimated_minutes_watched": round(views * rng.uniform(0.5, 4.0), 2),
            })
    return rows


def _write(table_name: str, rows: list[dict]) -> None:
    if not rows:
        return
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    path = SAMPLE_DIR / f"{table_name}.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {len(rows)} rows -> {path.relative_to(REPO_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate sample_data/ CSV fixtures mirroring the youtube_analytics schema.",
    )
    parser.add_argument("--snapshot-date", type=date.fromisoformat, default=None, help=(
        "Override the snapshot date (YYYY-MM-DD). Defaults to today's Phoenix date. "
        "Use to generate fixtures for testing stale-data paths."
    ))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot = args.snapshot_date or datetime.now(ZoneInfo("America/Phoenix")).date()
    print(f"Generating sample data for snapshot_date = {snapshot}")
    _write("video_metadata", generate_video_metadata(snapshot))
    _write("daily_video_stats", generate_daily_video_stats(snapshot))
    _write("daily_video_analytics", generate_daily_video_analytics(snapshot))
    _write("daily_traffic_sources", generate_daily_traffic_sources(snapshot))
    print()
    print(f"Sample dataset written to {SAMPLE_DIR.relative_to(REPO_ROOT)}/")
    print(
        "Point the analyzer at these CSVs instead of BigQuery by setting "
        "DATA_SOURCE=csv in your .env (or follow the README's CSV fallback section)."
    )


if __name__ == "__main__":
    main()
