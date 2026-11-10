# Schedule

The analyzer supports weekly Claude Code routines. The previous setup targeted
Monday at 9 a.m. America/Phoenix. The archive configuration below is a setup
procedure. Its GitHub authentication and retention path still need verification
inside the hosted runtime before a recurring run is enabled.

## Archive setup

1. Open [Claude Code Routines](https://claude.ai/code/routines). Create a new
   routine if the account has no analyzer registration. Use
   `.claude/commands/run-analyzer.md` and select the intended schedule and
   BigQuery connector.
2. Select the analyzer code repo and the separately approved private archive
   repo. The analyzer code checkout needs read access only. Set
   `REPORT_ARCHIVE_CHECKOUT` to the private checkout root and
   `REPORT_ARCHIVE_REPOSITORY` to its GitHub owner and repository.
3. Set `REPORT_DESTINATION=archive`, `REPORT_ARCHIVE_REQUIRED=1`, `BQ_PROJECT`
   and `BQ_DATASET`. The helper needs an authenticated `gh` for repository
   visibility and a GitHub origin for its readback. The helper holds before
   data queries if the hosted checkout uses a URL or credentials it cannot
   verify. Keep credentials in the routine environment.
4. Scope any authorized commit to the exact staged bundle path. Use the
   operator-approved private branch and an explicit push target such as
   `git push origin "HEAD:refs/heads/${archive_branch}"`. Use the schedule
   prompt to direct writes exclusively to that private checkout. Keep report
   data out of the analyzer code checkout's Git index.
5. Read back the task configuration. Use an authorized private test to confirm
   the selected repositories, GitHub authentication, write scope and readback
   from a fresh hosted session. A local fixture verifies local behavior only.

Artifacts stay in the ignored `.internal/channel-patterns/` directory until
the staging helper copies a verified run to
`records/channel-patterns/runs/<run-key>/` in the private checkout. Each run key
has one path. A different bundle at that path is a conflict. The SHA-256
manifest covers the report, summary and three canonical query results.
The next analyzer session reads calibration reports from a fetched revision
of the private default branch. Fixtures and incomplete runs stay out of
calibration.

## Retention readback

After the bundle reaches the private default branch, use the path and SHA-256
from staging to verify retention.

```bash
python3 scripts/private_report_archive.py --checkout "$REPORT_ARCHIVE_CHECKOUT" \
  --repository "$REPORT_ARCHIVE_REPOSITORY" --verify-retained "$bundle_path" "$manifest_sha256"
```

Use the returned revision in the retention receipt. Report pending review
if the bundle is on a branch only. Report a held transfer if the required
write or readback is unavailable. Preserve the local archive and the existing
receipts in either case. Stage only the returned path and use a non-force push.

## Local reruns and legacy output

Run `/run-analyzer` from the analyzer checkout. Local runs may keep their
artifacts in ignored storage. `DATA_SOURCE=csv` uses synthetic data and stays
local. The recipe uses reported transport and simulation warnings to identify
fixtures.

The optional legacy `REPORT_DESTINATION=notion` is for explicitly configured
local runs. It uses ignored storage and requires the Notion connector and
`NOTION_REPORT_PAGE_ID`. See [the runbook](runbook.md) for errors and
[the Claude Code Routines guide](https://code.claude.com/docs/en/routines) for
task controls.
