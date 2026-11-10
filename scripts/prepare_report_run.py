"""Select the report destination and reserve a private archive run directory."""

import argparse
from datetime import date, datetime
from hashlib import sha256
from itertools import count
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

ARCHIVE = Path(".internal/channel-patterns")
RUN_KEY = re.compile(r"(\d{4}-\d{2}-\d{2})(?:-([2-9]|[1-9][0-9]+))?", re.ASCII)
TRANSPORT_SOURCE = {"csv": "csv", "bq_cli": "bigquery", "bq_mcp": "bigquery"}
QUERY_FILES = ("data_health.json", "top_full_length_videos.json", "eligible_video_count.json")
AUDIT_CHECKS = {
    "six_sections_in_order", "empty_sections_render_with_explicit_body",
    "stale_table_disclaimers_present", "age_control_enforced", "cross_age_window_labeled",
    "trending_claims_have_minimum_age", "confidence_labels_present",
    "confidence_n_matches_comparison_set", "confidence_thresholds_correct", "no_em_dashes",
    "no_en_dashes_as_punctuation", "no_banned_vocab", "no_formulaic_openers",
    "first_person_plural_where_it_fits", "no_prior_report_citation",
    "multi_week_claims_self_contained", "numbers_match_underlying_query_results",
}


def private_directory(path: Path) -> None:
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("archive_directory_must_be_private")


def archive_root(repo: Path) -> Path:
    tracked = subprocess.check_output(["git", "ls-files", "--", str(ARCHIVE)], cwd=repo)
    # Ignoring the directory itself covers every attempt and artifact within it.
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", "--", str(ARCHIVE) + "/"],
        cwd=repo, capture_output=True, check=False,
    )
    if tracked or ignored.returncode:
        raise ValueError("archive_destination_must_be_ignored")

    internal = repo / ".internal"
    internal.mkdir(mode=0o700, exist_ok=True)
    if internal.is_symlink() or not internal.is_dir() or internal.stat().st_uid != os.getuid():
        raise ValueError("archive_parent_invalid")
    root = repo / ARCHIVE
    for directory in (root, root / "runs", root / "reports"):
        private_directory(directory)

    return root


def validate_destination(destination: str) -> None:
    if destination not in {"archive", "notion"}:
        raise ValueError("invalid_report_destination")
    checkout = os.environ.get("REPORT_ARCHIVE_CHECKOUT")
    repository = os.environ.get("REPORT_ARCHIVE_REPOSITORY")
    if bool(checkout) != bool(repository):
        raise ValueError("archive_checkout_and_repository_required_together")
    required = os.environ.get("REPORT_ARCHIVE_REQUIRED", "0")
    if required not in {"0", "1"}:
        raise ValueError("invalid_archive_required")
    cloud_session = os.environ.get("CLAUDE_CODE_REMOTE") == "true"
    if (required == "1" or cloud_session) and (
        destination != "archive" or (os.environ.get("DATA_SOURCE") != "csv" and not checkout)
    ):
        raise ValueError("archive_private_destination_required")


def prepare(repo: Path, destination: str, run_date: str) -> dict:
    if date.fromisoformat(run_date).isoformat() != run_date:
        raise ValueError("invalid_run_date")
    validate_destination(destination)
    root = archive_root(repo)
    for attempt in count(1):
        key = run_date if attempt == 1 else f"{run_date}-{attempt}"
        report = root / "reports" / f"{key}.md"
        if report.exists() or report.is_symlink():
            continue
        run = root / "runs" / key
        try:
            run.mkdir(mode=0o700)
        except FileExistsError:
            continue
        (run / "queries").mkdir(mode=0o700)
        return {"destination": destination, "artifact_root": str(ARCHIVE), "run_key": key}


def report_bytes(root: Path, key: str) -> bytes:
    if not RUN_KEY.fullmatch(key):
        raise ValueError("invalid_run_key")
    run = root / "runs" / key
    if run.is_symlink() or not run.is_dir():
        raise ValueError("archive_attempt_unavailable")
    report = root / "reports" / f"{key}.md"
    copy = run / "report.md"
    if any(path.is_symlink() or not path.is_file() for path in (report, copy)):
        raise ValueError("archive_report_missing")
    raw = report.read_bytes()
    if not raw.strip() or raw != copy.read_bytes():
        raise ValueError("archive_report_copy_mismatch")
    return raw


def audited_summary(path: Path, key: str) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("archive_summary_missing")
    return parse_summary(path.read_bytes(), key)


def parse_summary(raw: bytes, key: str) -> dict:
    summary = json.loads(raw)
    if (not isinstance(summary, dict) or summary.get("run_key") != key
            or summary.get("run_date") != key[:10] or summary.get("report_destination") != "archive"
            or summary.get("notion_write_ok") is not False or summary.get("errors") != []):
        raise ValueError("archive_summary_not_ready")
    audit = summary.get("voice_audit")
    checks = audit.get("checks_passed") if isinstance(audit, dict) else None
    if (not isinstance(checks, list) or not all(isinstance(check, str) for check in checks)
            or len(checks) != len(AUDIT_CHECKS) or set(checks) != AUDIT_CHECKS
            or not isinstance(summary.get("snapshot_dates"), dict)):
        raise ValueError("archive_audit_required")
    transport = summary.get("transport")
    source = TRANSPORT_SOURCE.get(transport) if isinstance(transport, str) else None
    warnings = summary.get("warnings")
    if (source is None or summary.get("data_source") != source or not isinstance(warnings, list)
            or not all(isinstance(warning, str) for warning in warnings)):
        raise ValueError("archive_source_provenance_required")
    return summary


def finished_time(summary: dict) -> datetime:
    try:
        value = datetime.fromisoformat(summary.get("run_finished_at", ""))
    except (TypeError, ValueError):
        raise ValueError("archive_run_finish_time_invalid") from None
    if value.utcoffset() is None:
        raise ValueError("archive_run_finish_time_invalid")
    return value


def query_artifacts(run: Path) -> dict[str, bytes]:
    queries = run / "queries"
    if queries.is_symlink() or not queries.is_dir():
        raise ValueError("archive_query_artifact_missing")
    artifacts = {}
    for name in QUERY_FILES:
        path = queries / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("archive_query_artifact_missing")
        artifacts[f"queries/{name}"] = path.read_bytes()
    return artifacts


def query_hashes(artifacts: dict[str, bytes]) -> dict[str, str]:
    hashes = {}
    for name in QUERY_FILES:
        path = f"queries/{name}"
        raw = artifacts[path]
        if not isinstance(json.loads(raw), (list, dict)):
            raise ValueError("archive_query_result_invalid")
        hashes[path] = sha256(raw).hexdigest()
    return hashes


def archive_status(summary: dict) -> str:
    if summary["transport"] == "csv" or any(
        warning.startswith("simulate_stale_") for warning in summary["warnings"]
    ):
        return "archived_fixture"
    return "archived_local"


def finalize(root: Path, key: str) -> dict:
    raw = report_bytes(root, key)
    run = root / "runs" / key
    summary = audited_summary(run / "summary.pending.json", key)
    finished_time(summary)
    summary.update(archive_status=archive_status(summary), report_sha256=sha256(raw).hexdigest(),
                   query_sha256=query_hashes(query_artifacts(run)))
    encoded = (json.dumps(summary, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()
    output = run / "summary.json"
    with tempfile.NamedTemporaryFile(dir=run, prefix=".summary-", delete=False) as temp:
        pending = Path(temp.name)
        temp.write(encoded)
        temp.flush()
        os.fsync(temp.fileno())
    try:
        try:
            os.link(pending, output)
        except FileExistsError:
            pass
        if output.is_symlink() or not output.is_file() or output.read_bytes() != encoded:
            raise ValueError("archive_summary_conflict")
    finally:
        pending.unlink()
    return {key: summary[key] for key in ("archive_status", "report_sha256", "query_sha256")}


def prior_reports(root: Path, run_date: str) -> dict:
    selected = {}
    skipped = []
    for report in sorted((root / "reports").glob("*.md")):
        match = RUN_KEY.fullmatch(report.stem)
        if not match:
            skipped.append({"run_key": None, "reason": "invalid_archive_filename"})
            continue
        if match[1] >= run_date:
            continue
        day, attempt = match[1], int(match[2] or 1)
        try:
            date.fromisoformat(day)
            raw = report_bytes(root, report.stem)
            run = root / "runs" / report.stem
            summary = audited_summary(run / "summary.json", report.stem)
            finished_time(summary)
            if summary.get("query_sha256") != query_hashes(query_artifacts(run)):
                raise ValueError("archive_query_hash_mismatch")
        except (OSError, ValueError, RecursionError) as error:
            skipped.append({"run_key": report.stem, "reason": error_code(error)})
            continue
        if archive_status(summary) != "archived_local" or summary.get("archive_status") != "archived_local":
            skipped.append({"run_key": report.stem, "reason": "archive_not_live_complete"})
            continue
        if summary.get("report_sha256") != sha256(raw).hexdigest():
            skipped.append({"run_key": report.stem, "reason": "archive_hash_mismatch"})
            continue
        if day not in selected or attempt > selected[day][0]:
            selected[day] = (attempt, report.stem)
    return {"selected": [{"run_date": day, "run_key": selected[day][1]} for day in sorted(selected)[-3:]],
            "skipped": skipped}


def error_code(error: Exception) -> str:
    message = str(error)
    if isinstance(error, ValueError) and re.fullmatch(r"(?:archive|invalid)_[a-z0-9_]+", message):
        return message
    return type(error).__name__


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", choices=["notion", "archive"], default="archive")
    parser.add_argument("--run-date", required=True)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--list-complete", action="store_true")
    action.add_argument("--finalize", metavar="RUN_KEY")
    args = parser.parse_args()
    try:
        repo = Path(__file__).resolve().parents[1]
        if args.list_complete or args.finalize:
            if args.destination != "archive" or date.fromisoformat(args.run_date).isoformat() != args.run_date:
                raise ValueError("invalid_archive_action")
            validate_destination(args.destination)
            root = archive_root(repo)
            if args.finalize:
                if args.finalize[:10] != args.run_date:
                    raise ValueError("archive_date_mismatch")
                plan = finalize(root, args.finalize)
            else:
                plan = prior_reports(root, args.run_date)
        else:
            plan = prepare(repo, args.destination, args.run_date)
    except (OSError, ValueError, RecursionError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Report operation held ({error_code(error)}).\n")
    print(json.dumps(plan))


if __name__ == "__main__":
    main()
