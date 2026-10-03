# Checkpoint v1.1.8 token mapping and paced publishing ? 2026-10-03

## Verified runtime state

- 31/31 System User tokens return HTTP 200 from Meta `/v22.0/me`.
- 100/100 Pages are verified and mapped to current Vault credentials.
- Page group `NEW` contains 100 Pages. Stale deleted groups were removed.
- Allocation with requested `3 Page/token` completes as 24 tokens ? 3 Pages and 7 tokens ? 4 Pages.
- No `Bm1` label remains in the Page API output.

## Fixes

- Allocation permits the intended 3?4 Page/token balance when the remainder is one Page above the requested target.
- Allocation returns dry-run/effective-limit/load details and the UI offers a one-click retry.
- Fixed `message is not defined` error in allocation failure handling.
- Page/token assignment now uses Meta owner names rather than stale import labels.
- Health sync checks credential status only and does not silently rebalance Page ownership.
- Scheduled posts preserve the selected token and per-token gap; different tokens may run concurrently.
- Scheduler records token API usage and revalidates the exact queued token before publishing.

## Verification

- `138 passed, 10 subtests passed` in the focused release guard, token/Page, scheduling, and posting pacing suites. Full installer build gate also passed its configured groups: 42 + 25 + 55 + 61 tests.
- Live dry run: 100 Pages, effective limit 4, 31 active tokens.
- Live assignment: 100 Pages, distribution 24?3 and 7?4; mapping health 100 verified, 31 mapped credentials, 0 unhealthy.

## GitHub release

- Source commit: `6cd87e5` on `release/v1.1.8`.
- Tag: `v1.1.8-token-fix1`.
- Installer: `Highlight_Desktop_Test_Setup_v1.1.8-token-fix1.exe`, 703229440 bytes.
- SHA-256: `76b788ae77cd5d7fbb766619dd80cb082e7b9cce30bd0d7e69ddff3be080a6f1`.
- Release asset verified as `uploaded` with matching size through GitHub API.
- Live Meta publish remains to be validated by the operator's test; Meta can still reject a valid token/Page due to platform policy.
