"""Exercise report retention without network access or provider credentials."""

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import prepare_report_run as local
import private_report_archive as private


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.source = Path(folder.name) / "analyzer"
        self.target = Path(folder.name) / "private-content"
        self.origin = Path(folder.name) / "private-origin.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.origin)], check=True)
        for repo in (self.source, self.target):
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (self.source / ".gitignore").write_text(".internal/\n")
        self.git("config", "user.email", "archive-fixture@example.invalid")
        self.git("config", "user.name", "Archive Fixture")
        self.git("checkout", "-q", "-b", "main")
        self.git("commit", "-q", "--allow-empty", "-m", "Initialize archive fixture")
        self.git("push", "-q", str(self.origin), "HEAD:refs/heads/main")
        subprocess.run(
            ["git", "-C", str(self.target), "remote", "add", "origin",
             "https://github.com/example/private-content.git"],
            check=True,
        )
        self.repository = "example/private-content"
        self.gh = {"private": True, "visibility": "private", "full_name": self.repository,
                   "default_branch": "main"}
        original = private._command

        def command(args, checkout):
            if args[0] == "gh":
                self.assertEqual(args[1:], [
                    "api", "--hostname", "github.com", "--method", "GET",
                    "repos/example/private-content",
                ])
                return json.dumps(self.gh)
            if args[:2] == ["git", "fetch"]:
                args = [str(self.origin) if arg == "origin" else arg for arg in args]
            return original(args, checkout)

        mock = patch.object(private, "_command", command)
        mock.start()
        self.addCleanup(mock.stop)

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.target, text=True).strip()

    def push_fixture(self, *, branch="main"):
        self.git("add", "--", str(private.DESTINATION))
        self.git("commit", "-q", "-m", "Commit synthetic report fixture")
        self.git("push", "-q", str(self.origin), f"HEAD:refs/heads/{branch}")

    def complete(self, day, *, content=b"# Synthetic test report\n", transport="bq_mcp", hour=12,
                 finish_time=None, missing_query=None):
        key = local.prepare(self.source, "archive", day)["run_key"]
        root = self.source / local.ARCHIVE
        run = root / "runs" / key
        (root / "reports" / f"{key}.md").write_bytes(content)
        (run / "report.md").write_bytes(content)
        for name in private.QUERY_FILES:
            if name != missing_query:
                (run / "queries" / name).write_text('[{"synthetic":true}]\n')
        summary = {
            "run_key": key, "run_date": day,
            "run_finished_at": finish_time or f"{day}T{hour:02d}:00:00+00:00",
            "report_destination": "archive", "notion_write_ok": False, "errors": [],
            "snapshot_dates": {}, "voice_audit": {"checks_passed": sorted(local.AUDIT_CHECKS)},
            "transport": transport, "data_source": local.TRANSPORT_SOURCE[transport],
            "warnings": [],
        }
        (run / "summary.pending.json").write_text(json.dumps(summary))
        local.finalize(root, key)
        return key

    def stage(self, key):
        return private.stage(self.source, self.target, self.repository, key)

    def test_copy_replays_and_preserves_hashes(self):
        key = self.complete("2026-01-01")
        result = self.stage(key)
        self.assertEqual(result, self.stage(key))
        output = self.target / result["path"]
        self.assertEqual(result["manifest_sha256"],
                         sha256((output / "manifest.json").read_bytes()).hexdigest())
        self.assertEqual((output / "report.md").read_bytes(), b"# Synthetic test report\n")
        self.assertEqual(set(output.glob("*.json")), {output / "summary.json", output / "manifest.json"})
        self.assertFalse(list(self.source.glob("records/**/*")))
        (output / "report.md").write_text("modified")
        with self.assertRaisesRegex(ValueError, "hash_mismatch"):
            self.stage(key)

    def test_refuses_public_or_mismatched_origin_before_artifact_write(self):
        key = self.complete("2026-01-01")
        self.gh.update(private=False, visibility="public")
        with self.assertRaisesRegex(ValueError, "not_private"):
            self.stage(key)
        self.gh.update(private=True, visibility="private")
        subprocess.run([
            "git", "-C", str(self.target), "remote", "set-url", "--push", "origin",
            "https://github.com/example/public.git",
        ], check=True)
        with self.assertRaisesRegex(ValueError, "origin_mismatch"):
            self.stage(key)
        self.assertFalse((self.target / private.DESTINATION).exists())

    def test_refuses_fixture_and_missing_query(self):
        key = self.complete("2026-01-01", transport="csv")
        with self.assertRaisesRegex(ValueError, "not_live_complete"):
            self.stage(key)
        key = self.complete("2026-01-01")
        (self.source / local.ARCHIVE / "runs" / key / "queries"
         / private.QUERY_FILES[0]).unlink()
        with self.assertRaisesRegex(ValueError, "artifact_missing"):
            self.stage(key)
        self.assertFalse((self.target / private.DESTINATION).exists())

    def test_no_finalization_until_query_and_finish_time_are_valid(self):
        with self.assertRaisesRegex(ValueError, "run_finish_time_invalid"):
            self.complete("2026-01-01", finish_time="2026-01-01T12:00:00")
        with self.assertRaisesRegex(ValueError, "query_artifact_missing"):
            self.complete("2026-01-02", missing_query=private.QUERY_FILES[0])
        root = self.source / local.ARCHIVE
        self.assertFalse(list(root.glob("runs/*/summary.json")))

    def test_pinned_query_and_fixed_run_path_prevent_conflicting_replays(self):
        key = self.complete("2026-01-01")
        staged = self.stage(key)
        self.assertEqual(staged["path"], f"{private.DESTINATION}/{key}")
        run = self.source / local.ARCHIVE / "runs" / key
        query = run / "queries" / private.QUERY_FILES[0]
        query.write_text("[]\n")
        with self.assertRaisesRegex(ValueError, "query_hash_mismatch"):
            self.stage(key)
        (run / "summary.json").unlink()
        local.finalize(self.source / local.ARCHIVE, key)
        with self.assertRaisesRegex(ValueError, "run_conflict"):
            self.stage(key)
        self.assertEqual(len(list((self.target / private.DESTINATION).iterdir())), 1)

    def test_required_destination_and_legacy_storage_are_enforced(self):
        config = {"REPORT_ARCHIVE_REQUIRED": "1", "DATA_SOURCE": "bq_mcp"}
        with patch.dict(os.environ, config, clear=True):
            with self.assertRaisesRegex(ValueError, "private_destination_required"):
                local.prepare(self.source, "archive", "2026-01-01")
            with patch.dict(os.environ, {"REPORT_ARCHIVE_CHECKOUT": str(self.target)}):
                with self.assertRaisesRegex(ValueError, "required_together"):
                    local.prepare(self.source, "archive", "2026-01-01")
            with patch.dict(os.environ, {"DATA_SOURCE": "csv"}):
                self.assertEqual(local.prepare(self.source, "archive", "2026-01-01")["run_key"],
                                 "2026-01-01")
            with self.assertRaisesRegex(ValueError, "private_destination_required"):
                local.prepare(self.source, "notion", "2026-01-01")
        self.assertEqual(local.prepare(self.source, "notion", "2026-01-01")["artifact_root"],
                         str(local.ARCHIVE))
        with patch.dict(os.environ, {"CLAUDE_CODE_REMOTE": "true"}, clear=True):
            with self.assertRaisesRegex(ValueError, "private_destination_required"):
                local.prepare(self.source, "archive", "2026-01-01")

    def test_refuses_extra_remote_and_push_default(self):
        key = self.complete("2026-01-01")
        self.git("remote", "add", "unsafe", "https://github.com/example/public.git")
        with self.assertRaisesRegex(ValueError, "unexpected_remote"):
            self.stage(key)
        self.git("remote", "remove", "unsafe")
        self.git("config", "remote.pushDefault", "unsafe")
        with self.assertRaisesRegex(ValueError, "push_override"):
            self.stage(key)

    def test_refuses_symlinks(self):
        key = self.complete("2026-01-01")
        (self.target / "records").symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink_rejected"):
            self.stage(key)
        self.assertFalse((self.source / "channel-patterns").exists())

    def test_replay_rejects_unreviewed_extra_files(self):
        key = self.complete("2026-01-01")
        result = self.stage(key)
        (self.target / result["path"] / "extra.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "paths_mismatch"):
            self.stage(key)

    def test_prior_selects_distinct_dates_and_skips_tampered_artifacts(self):
        for day in ("2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"):
            self.stage(self.complete(day))
        retry = self.stage(self.complete("2026-01-03", hour=13))
        bad = self.stage(self.complete("2026-01-02", hour=15))
        (self.target / bad["path"] / "summary.json").write_text("{}")
        self.push_fixture()
        (self.target / retry["path"] / "report.md").write_text("unstaged local change")
        result = private.prior(self.source, self.target, self.repository, "2026-01-04")
        self.assertEqual(result["revision"], self.git("rev-parse", "HEAD"))
        self.assertEqual(result["skipped"], 1)
        self.assertEqual([row["run_date"] for row in result["selected"]],
                         ["2026-01-01", "2026-01-02", "2026-01-03"])
        self.assertEqual(result["selected"][-1]["report"], retry["path"] + "/report.md")

    def test_staged_and_branch_only_artifacts_do_not_count_as_retained(self):
        result = self.stage(self.complete("2026-01-01"))
        args = (self.source, self.target, self.repository, result["path"], result["manifest_sha256"])
        with self.assertRaisesRegex(ValueError, "paths_mismatch"):
            private.retained(*args)
        self.push_fixture(branch="pending")
        self.assertEqual(private.prior(self.source, self.target, self.repository, "2026-01-02")["selected"], [])
        with self.assertRaisesRegex(ValueError, "paths_mismatch"):
            private.retained(*args)
        self.git("push", "-q", str(self.origin), "HEAD:refs/heads/main")
        self.assertEqual(private.retained(*args), {**result, "status": "retained_private",
                                                  "revision": self.git("rev-parse", "HEAD")})
        with self.assertRaisesRegex(ValueError, "retained_manifest_mismatch"):
            private.retained(*args[:-1], "0" * 64)


if __name__ == "__main__":
    unittest.main()
