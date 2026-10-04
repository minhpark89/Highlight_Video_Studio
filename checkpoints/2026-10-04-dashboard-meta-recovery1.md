# Dashboard and existing Meta upload recovery — 2026-10-04

Release revision: `1.1.9-dashboard-meta-recovery1`, branch `release/v1.1.9`.

The user requested editable Folder Binding on new Page groups, exhaustive post totals, a first/default Trang chủ dashboard, investigation of the remaining post, and an app recovery action. Deployment is authorized by the session's preceding confirmation. Preserve all mutable data, Page/token bindings, user groups, frozen comments, the existing upload ID, and paused rendering. Do not publish to GitHub.

## Changes

- Trang chủ is the first/default tab, with actual local metrics, seven-day activity, status donut, affected posts, and scheduler/render/comment health.
- Exhaustive shared classification accounts for all 200 posts, including ordinary processing and unknown states. Published/failed records without dates are excluded from the chart and reported.
- New group Folder Binding is editable and has an app directory browser; editing a group has the same browser.
- Diagnostic GET inspects the existing Meta object through the exact original verified credential and returns safe selected phase fields. It does not rewrite the ledger.
- An explicit app confirmation can send one Finish request to the existing upload. Fresh HTTP 200, matching upload ID, completed upload, unstarted processing/publication, original credential, cooldown checks, valid native schedule, and a durable claim before the write are required. No initialization or video transfer occurs. The scheduler lock and persistent claim prevent replay; accepted/unknown Finish responses remain processing until independently verified.
- Ordinary worker reconciliation saves Meta phase observations and retains the original publishing error for future diagnosis.

## Outstanding post evidence

- Local post: `post_1791087110_aaee5d`.
- Title: Police Impersonator Gets Caught Pulling Over Real Drivers.
- Page: Zachary Grant Carter (`1346447641878736`).
- Existing Meta upload: `1107514081727419`; original Token ID `tok_1791016013_6`.
- Independent GET observed upload_complete, 61094086 bytes, processing/publishing not_started, copyright complete without matches, HTTP 200, and no published Reel permalink.
- The old worker did not retain the detailed historical Finish response. Its precise historical failure cause cannot be asserted. No Meta recovery write was performed while building or testing this change.

## Validation

- Full suite: 378 passed, 3 skipped, 29 subtests passed.
- New diagnostic/dashboard tests: 26 passed, including changed/missing HTTP state, exact credentials, durable recovery fence, cooldown/persistence failures, expired native schedule and existing-ID-only transport.
- Isolated browser smoke: zero JavaScript errors, first/default Trang chủ, 200/199/1 metrics, one processing row, editable/selected folder included in save payload, mocked one-time Finish and disabled repeat. Screenshots inspected at 1600/1280 widths.
- Python compilation and HTML mirror equality passed.
- Evidence/tools: `E:/OPENCLAW/BOB/support/dashboard-meta-recovery1/`.

Build/deployment evidence will be appended after packaging and installation. Retain older installers and checkpoints.
