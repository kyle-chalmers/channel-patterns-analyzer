"""Stage completed analyzer runs in a verified private GitHub checkout."""

import argparse
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import tempfile

from prepare_report_run import (
    QUERY_FILES, RUN_KEY, archive_root, archive_status, error_code, finished_time,
    parse_summary, query_artifacts, query_hashes, report_bytes,
)

DESTINATION = Path("records/channel-patterns/runs")
BUNDLE_FILES = {"report.md", "summary.json", *(f"queries/{name}" for name in QUERY_FILES)}
REPO_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+")


def _command(args: list[str], checkout: Path) -> str:
    result = subprocess.run(args, cwd=checkout, capture_output=True, text=True, timeout=20)
    if result.returncode:
        # A provider error may contain an authenticated remote URL.
        raise ValueError("archive_repository_verification_failed")
    return result.stdout.strip()


def private_checkout(checkout: Path, repository: str, source: Path) -> tuple[Path, str]:
    checkout = checkout.resolve(strict=True)
    source = source.resolve()
    if (checkout.is_relative_to(source) or source.is_relative_to(checkout)
            or not REPO_NAME.fullmatch(repository)
            or ".." in repository):
        raise ValueError("invalid_archive_repository")
    top = _command(["git", "rev-parse", "--show-toplevel"], checkout)
    if Path(top).resolve() != checkout:
        raise ValueError("archive_checkout_must_be_repository_root")
    if _command(["git", "remote"], checkout) != "origin":
        raise ValueError("archive_unexpected_remote")
    config_names = _command(["git", "config", "--name-only", "--list"], checkout).splitlines()
    if any(key in {"remote.pushdefault", "remote.origin.push"} or
           (key.startswith("branch.") and key.endswith(".pushremote")) for key in config_names):
        raise ValueError("archive_push_override")

    allowed = {
        f"{prefix}{repository}{suffix}".lower()
        for prefix in ("https://github.com/", "git@github.com:", "ssh://git@github.com/")
        for suffix in ("", ".git")
    }
    for mode in ([], ["--push"]):
        urls = _command(["git", "remote", "get-url", *mode, "--all", "origin"], checkout)
        if urls.lower() not in allowed:
            raise ValueError("archive_origin_mismatch")

    info = json.loads(_command(
        ["gh", "api", "--hostname", "github.com", "--method", "GET", f"repos/{repository}"],
        checkout,
    ))
    if (not isinstance(info, dict) or info.get("private") is not True
            or info.get("visibility") != "private" or not isinstance(info.get("full_name"), str)
            or info["full_name"].lower() != repository.lower()):
        raise ValueError("archive_repository_not_private")
    default_branch = info.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch or default_branch.startswith("-"):
        raise ValueError("archive_default_branch_invalid")
    _command(["git", "check-ref-format", f"refs/heads/{default_branch}"], checkout)
    return checkout, default_branch


def _default_revision(checkout: Path, branch: str) -> str:
    remote_ref = f"refs/remotes/origin/{branch}"
    _command([
        "git", "fetch", "--no-tags", "--no-recurse-submodules", "--no-write-fetch-head",
        "--refmap=", "origin", f"refs/heads/{branch}:{remote_ref}",
    ], checkout)
    return _command(["git", "rev-parse", "--verify", f"{remote_ref}^{{commit}}"], checkout)


def _git_bytes(checkout: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=checkout, capture_output=True, timeout=20)
    if result.returncode:
        raise ValueError("archive_git_evidence_unavailable")
    return result.stdout


def _contained(base: Path, relative: Path) -> Path:
    path = base
    for part in relative.parts:
        path /= part
        if path.is_symlink():
            raise ValueError("archive_symlink_rejected")
    return path


def _file(root: Path, relative: Path) -> bytes:
    path = _contained(root, relative)
    if not path.is_file():
        raise ValueError("archive_artifact_missing")
    return path.read_bytes()


def _encoded(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()


def _bundle(checkout: Path, key: str) -> dict[str, bytes]:
    root = archive_root(checkout)
    report = report_bytes(root, key)
    run = _contained(root, Path("runs") / key)
    bundle = {"report.md": report, "summary.json": _file(run, Path("summary.json")),
              **query_artifacts(run)}
    _validate_bundle(key, bundle)
    return bundle


def _validate_bundle(key: str, bundle: dict[str, bytes]) -> dict:
    if not RUN_KEY.fullmatch(key) or date.fromisoformat(key[:10]).isoformat() != key[:10]:
        raise ValueError("archive_run_directory_invalid")
    summary = parse_summary(bundle["summary.json"], key)
    if (archive_status(summary) != "archived_local" or summary.get("archive_status") != "archived_local"
            or summary.get("report_sha256") != sha256(bundle["report.md"]).hexdigest()):
        raise ValueError("archive_run_not_live_complete")
    if summary.get("query_sha256") != query_hashes(bundle):
        raise ValueError("archive_query_hash_mismatch")
    finished_time(summary)
    return summary


def _manifest(key: str, bundle: dict[str, bytes]) -> bytes:
    return _encoded({
        "run_key": key,
        "version": 1,
        "sha256": {name: sha256(data).hexdigest() for name, data in bundle.items()},
    })


def _read_bundle(path: Path) -> tuple[dict, dict[str, bytes]]:
    if path.is_symlink() or not path.is_dir():
        raise ValueError("archive_run_directory_invalid")
    queries = _contained(path, Path("queries"))
    if ({item.name for item in path.iterdir()} != {"report.md", "summary.json", "manifest.json", "queries"}
            or not queries.is_dir() or {item.name for item in queries.iterdir()} != set(QUERY_FILES)):
        raise ValueError("archive_bundle_paths_mismatch")
    bundle = {name: _file(path, Path(name)) for name in BUNDLE_FILES}
    if _file(path, Path("manifest.json")) != _manifest(path.name, bundle):
        raise ValueError("archive_bundle_hash_mismatch")
    return _validate_bundle(path.name, bundle), bundle


def stage(source: Path, checkout: Path, repository: str, key: str) -> dict:
    target, _ = private_checkout(checkout, repository, source)
    bundle = _bundle(source, key)
    manifest = _manifest(key, bundle)
    directory = _contained(target, DESTINATION)
    output = directory / key
    if output.exists() or output.is_symlink():
        if _read_bundle(output)[1] != bundle:
            raise ValueError("archive_run_conflict")
    else:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".pending-", dir=directory) as temp:
            pending = Path(temp) / output.name
            for name, data in {**bundle, "manifest.json": manifest}.items():
                path = pending / name
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with path.open("xb") as stream:
                    stream.write(data)
            _read_bundle(pending)
            try:
                pending.rename(output)
            except OSError:
                if not output.exists():
                    raise
                if _read_bundle(output)[1] != bundle:
                    raise ValueError("archive_run_conflict") from None
    if _read_bundle(output)[1] != bundle:
        raise ValueError("archive_run_conflict")
    return {"status": "staged_private", "path": str(output.relative_to(target)),
            "manifest_sha256": sha256(manifest).hexdigest()}


def _git_bundle(target: Path, revision: str, path: str) -> tuple[dict, bytes]:
    entries = {}
    raw = _git_bytes(target, "ls-tree", "-r", "-z", "--full-tree", revision, "--", path)
    for line in raw.decode().split("\0"):
        if not line:
            continue
        identity, name = line.split("\t", 1)
        mode, kind, blob = identity.split()
        if mode not in {"100644", "100755"} or kind != "blob" or not name.startswith(f"{path}/"):
            raise ValueError("archive_bundle_paths_mismatch")
        entries[name[len(path) + 1:]] = blob
    if set(entries) != BUNDLE_FILES | {"manifest.json"}:
        raise ValueError("archive_bundle_paths_mismatch")
    data = {name: _git_bytes(target, "cat-file", "blob", blob) for name, blob in entries.items()}
    manifest = data.pop("manifest.json")
    key = Path(path).name
    if manifest != _manifest(key, data):
        raise ValueError("archive_bundle_hash_mismatch")
    return _validate_bundle(key, data), manifest


def retained(source: Path, checkout: Path, repository: str, path: str, manifest_sha256: str) -> dict:
    key = Path(path).name
    if path != (DESTINATION / key).as_posix() or not RUN_KEY.fullmatch(key):
        raise ValueError("archive_run_directory_invalid")
    target, branch = private_checkout(checkout, repository, source)
    revision = _default_revision(target, branch)
    _, manifest = _git_bundle(target, revision, path)
    if sha256(manifest).hexdigest() != manifest_sha256:
        raise ValueError("archive_retained_manifest_mismatch")
    return {"status": "retained_private", "revision": revision, "path": path,
            "manifest_sha256": manifest_sha256}


def prior(source: Path, checkout: Path, repository: str, run_date: str) -> dict:
    if date.fromisoformat(run_date).isoformat() != run_date:
        raise ValueError("invalid_run_date")
    target, branch = private_checkout(checkout, repository, source)
    revision = _default_revision(target, branch)
    listing = _git_bytes(target, "ls-tree", "-d", "--name-only", "-z", revision, "--",
                         f"{DESTINATION}/").decode().split("\0")
    newest = {}
    skipped = 0
    for path in filter(None, listing):
        key = Path(path).name
        if not RUN_KEY.fullmatch(key) or key[:10] >= run_date:
            continue
        try:
            summary, _ = _git_bundle(target, revision, path)
        except (OSError, ValueError, RecursionError):
            skipped += 1
            continue
        day = summary["run_date"]
        candidate = (finished_time(summary), f"{path}/report.md")
        if day not in newest or candidate > newest[day]:
            newest[day] = candidate
    return {"revision": revision, "selected": [
        {"run_date": day, "report": newest[day][1]}
        for day in sorted(newest)[-3:]
    ], "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--verify-checkout", action="store_true")
    action.add_argument("--stage", metavar="RUN_KEY")
    action.add_argument("--prior", metavar="RUN_DATE")
    action.add_argument("--verify-retained", nargs=2, metavar=("PATH", "MANIFEST_SHA256"))
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    try:
        if args.verify_checkout:
            target, branch = private_checkout(args.checkout, args.repository, source)
            result = {"status": "private_checkout_verified", "default_branch": branch,
                      "revision": _default_revision(target, branch)}
        elif args.stage:
            result = stage(source, args.checkout, args.repository, args.stage)
        elif args.verify_retained:
            result = retained(source, args.checkout, args.repository, *args.verify_retained)
        else:
            result = prior(source, args.checkout, args.repository, args.prior)
    except (ValueError, OSError, RecursionError, subprocess.SubprocessError) as error:
        parser.exit(2, f"Private report archive held ({error_code(error)}).\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
