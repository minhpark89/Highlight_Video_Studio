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

- `113 passed` across token/page allocation, scheduling, and posting pacing tests.
- Live dry run: 100 Pages, effective limit 4, 31 active tokens.
- Live assignment: 100 Pages, distribution 24?3 and 7?4; mapping health 100 verified, 31 mapped credentials, 0 unhealthy.
