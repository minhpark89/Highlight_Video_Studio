# Dashboard Insights 1 — 2026-10-04

Release revision: `1.1.9-dashboard-insights1`, branch `release/v1.1.9`.

## User request

Add Followers, Reach 7 ngày, Tương tác and Views cards to Trang chủ, deploy this revision to GitHub, provide a downloadable installer and preserve a checkpoint so another session can continue fixing from it.

## Implementation

- `web/page_insights.py` reads Meta Page analytics through the exact verified Page/token binding already stored by the app. It caches only selected aggregate fields and daily series under the ignored local file `data/page_insights.json`.
- Dashboard cards show real values, coverage, freshness and per-Page details. Missing values remain `—`; the UI does not turn missing permissions or missing data into zero.
- Followers uses current `followers_count`. Tương tác uses `page_post_engagements` and Views uses `page_media_view`, summed across the selected Page scope for the seven complete days. Each Page can be selected independently.
- Reach remains visible but explicitly reports that Meta's current API rejected the legacy `page_impressions_unique` metric. It is never substituted with Views and is never presented as zero.
- Sync is explicit through **Đồng bộ Meta**, bounded by a five-minute per-Page cooldown, exact verified credentials, token health and a single in-process sync fence. HTTP failures are sanitized; no access token is written to the cache or response.
- Sync is read-only on Meta. Only the local analytics cache and existing token usage counters are updated. It never changes posts, groups, Page bindings, render state or publishing state.

## Evidence and verification

- Full suite: **390 passed, 3 skipped, 29 subtests passed**.
- New Insights tests cover date mapping, unsupported Reach, partial Page coverage, invalid persisted values, credential/cooldown gates, cache-period invalidation, duplicate sync fencing and route validation.
- Isolated browser smoke: no JavaScript errors; cards show fixture values Followers 64, Tương tác 2, Views 269 and Reach `—`; sparkline renders, Page selector survives refresh, folder picker, existing Meta diagnosis and one-time mocked Finish still pass at 1600/1280 widths.
- Screenshots: `support/dashboard-insights1/evidence/dashboard-1600.png`, `dashboard-1280.png`.
- Live read-only Meta probe for Page `1346447641878736`: Followers 0, Tương tác 2, Views 269 for the current seven-day complete window; Reach metric rejected by Graph API code 100. Probe evidence: `support/dashboard-insights1/evidence/meta_probe.json` and `live_metrics_one_page.json`.
- Source HTML mirrors are byte-identical and Python modules compile.

## Deployment continuation

Build and GitHub release assets are appended after packaging. The prior `1.1.9-dashboard-meta-recovery1` installer and checkpoint remain untouched. The current live runtime is not replaced until the new installer is built and independently verified. Do not invoke the existing Meta Finish recovery action during this revision.

## Installation and first test

1. Download `Highlight_Desktop_Test_Setup_v1.1.9-dashboard-insights1.exe` from release `v1.1.9-dashboard-insights1`. Verify the SHA-256 using the adjacent `.sha256` asset.
2. Use the installer to update the existing installation. The installer backs up and preserves mutable ledgers, groups, credentials, outputs, config and the entire local `data/` directory. Do not manually replace a populated `posts.json` with the empty packaged seed.
3. Open **Trang chủ**. Select one Page under **Hiệu quả Fanpage**, then click **Đồng bộ Meta**. The request starts one background analytics worker; the UI displays progress and cached results.
4. Confirm Followers, Tương tác and Views show the available Meta counts. A real Meta zero displays `0`; unavailable data displays `—` with a reason. Check the per-Page detail table and coverage before treating a partial total as complete.
5. If desired, select **Tất cả Fanpage** and sync all Pages. The service honors the per-Page five-minute cooldown and stops reading a credential when Meta reports rate limiting. The dashboard's 30-second redraw reads cached data; it does not poll Graph for every page automatically.

## Code map and contracts for the next session

- `web/page_insights.py`: cache schema 1, Graph parsing, date window, safe missing states, verified credential resolution, per-Page sync cooldown and single background worker. `period_for()` uses the seven complete UTC calendar days; daily Meta rows use their exclusive `end_time` minus one calendar day. This mapping was independently checked against actual Graph results.
- `web/app.py`: `/api/dashboard/summary` embeds cached Insights. `GET /api/dashboard/insights?page_id=` selects cached scope; `POST /api/dashboard/insights/sync` accepts JSON `{ "page_id": "" }` for all Pages or a known Page ID. Both validate Page selection; summary/GET do not call Meta.
- `web/templates/index.html`: cards, Page selector, per-Page detail table, SVG sparklines, explicit sync and local progress polling. `web/index.html` must remain an exact mirror.
- `tests/test_page_insights.py`: focused analytics regressions. `tests/test_dashboard_diagnostics.py`: total partition, folder browser and safe existing-upload recovery. `tests/test_installer_data_preservation.py`: installer preservation contract.
- `src/publisher/page_manager.py`: `resolve_verified_mapping()` checks exact credential fingerprint and verified Page ID. Do not bypass this with a guessed/default Page token.
- `src/publisher/token_vault.py`: `record_usage()` records Graph headers against the original Token ID. `multi_pc/publishing_settings.py:credential_ready()` gates analytics and publishing through token health.
- Cache path: `<canonical install root>/data/page_insights.json`. It contains Page IDs, check times, periods, selected numeric metrics, safe reason states and observed follower history. It has no raw tokens and is excluded from Git/release seeds. The installer preserves it through the existing `data/` preservation rule.
- States: `not_synced`, `missing_binding`, `cooldown`, `permission`, `unsupported`, `no_data`, `incomplete`, `error`, `ok`. Only numeric, nonnegative, finite `ok` values contribute to totals. Coverage counts distinct Page IDs. Missing or incomplete daily data cannot become an invented zero.
- Reach uses one Meta weekly unique value when supported; it never sums seven daily unique reach values. Across Pages, the aggregate can count the same person more than once. The currently tested v22.0 API rejects this legacy metric; the card reports that explicitly.
- Followers' tiny chart only appears after at least two observed daily snapshots. No historical follower counts or growth percentages are invented for a first sync.

## Debugging guide

- `— / Cần Sync Page`: refresh the Page through its verified Token in Page/Token management, then sync Insights. Keep Page/token bindings and original posting credentials intact.
- `— / Token thiếu quyền`: verify Meta permissions including `read_insights` and `pages_read_engagement`, Page access and token validity. Publishing permission alone does not imply Insights permission.
- `— / Meta không còn cung cấp`: check the current Graph metric contract before changing code. For Reach, do not substitute `page_media_view`, `page_views_total`, or summed daily unique counts under the Reach label.
- `— / Meta chưa trả đủ 7 ngày`: inspect selected daily values and exclusive end dates in a read-only Graph request. Keep missing dates unknown rather than fill them with zero.
- Partial aggregate: inspect the detail table's metric reasons and Page coverage. If the cache window is from yesterday, seven-day values are invalidated until the next sync; current follower snapshots remain dated and marked stale.
- Sync cannot restart immediately: a running worker fences duplicate requests and a successful/failed fresh per-Page check waits five minutes. A new process can resume by checking the remaining stale Pages; reads are safe to repeat.
- Interrupted sync/cache persistence failure: the last atomic cache remains readable and progress exposes a generic error. Do not dump exception URLs or vault contents into logs/evidence.
- API/version changes: update `GRAPH_BASE`, metric queries and parser tests together; use separate metric probes where a grouped query fails because one metric was removed.

Run from the repository root: `python -m pytest -q --no-header`. Focused checks: `python -m pytest tests/test_page_insights.py tests/test_dashboard_diagnostics.py -q --no-header`. Compile changed Python modules and compare the two HTML mirrors, then perform browser smoke for first/default Trang chủ, metric values/missing states, scope persistence and sync progress.

## Previous fixes included in this installer

This revision also contains the editable new-group Folder Binding and directory picker, complete 200-post status partition, default Trang chủ dashboard, verified Page/Token grouping and existing-upload Meta diagnosis/recovery from prior local commits. These changes had not yet been published to GitHub; publishing `release/v1.1.9` includes them together.

At the last verified live runtime `http://127.0.0.1:63432`, revision `1.1.9-dashboard-meta-recovery1` retained 200 unique posts (199 published, 1 processing), 199 posted comments, 130 verified Pages, groups NEW/NEW 2/NEW PAGE 2, token groups NEW/NEW 2, 4 publishing workers and paused/idle rendering. This Insights revision is packaged for the user to download and install; do not silently replace the live installation while publishing the GitHub release.

The pending post is `post_1791087110_aaee5d`, **Police Impersonator Gets Caught Pulling Over Real Drivers**, Page Zachary Grant Carter (`1346447641878736`), retained Meta upload `1107514081727419`, original Token ID `tok_1791016013_6`. The earlier independent GET observed upload_complete, 61094086 bytes, processing/publishing not_started, copyright clear and no published Reel permalink. Old detailed Finish response was lost, so the historical cause is uncertain. The app's **Kiểm tra Meta → Hoàn tất video đã upload** requires a fresh eligible state and explicit user confirmation, and durably fences one Finish for the retained object. Never re-upload this post merely to test the release.

Previous checkpoints: `checkpoints/2026-10-04-dashboard-meta-recovery1.md`, `checkpoints/2026-10-04-meta-token-groups1.md`, `checkpoints/2026-10-04-meta-firstcomment3.md`.

Local evidence/helpers: `E:/OPENCLAW/BOB/support/dashboard-insights1/`. Public source repository: `https://github.com/minhpark89/Highlight_Video_Studio`, branch `release/v1.1.9`. Release assets are the installer, its SHA-256 file and a standalone copy of this checkpoint, for use without access to this machine's support folder.

## Built artifact — 2026-10-04 15:33 (Asia/Saigon)

- Installer revision: **1.1.9-dashboard-insights1**.
- Packaged code commit: **3aec707df46e158301e0da2e717478dbc5e5de91**, source_dirty=false.
- Build gates passed: hardware/local MVP/phase 1, release guards, Page/token sync, publishing/scheduling, native Meta handoff, First Comments, installer data preservation and Whisper fallback suites. The focused Insights suite passed again after the final token rate-limit gate change.
- Installer size: **680730112 bytes**.
- SHA-256: **874ed70ef542378847d45db9bcf04169eab085736f1a3272dcf6655f6f686c5f**.
- Payload verification passed for the app, both HTML mirrors, dashboard, new Insights module, Meta diagnosis/recovery, scheduler, posting settings and token vault. Packaged post seed is empty; runtime/user state and credential values are absent.
- Local installer: `E:/OPENCLAW/BOB/source-worktree/release/Highlight_Desktop_Test_Setup_v1.1.9-dashboard-insights1.exe`.
- Release tag: `v1.1.9-dashboard-insights1`; publication verification is recorded in the current branch checkpoint after upload. This standalone checkpoint is attached with the installer and checksum.
- GitHub release URL: `https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.1.9-dashboard-insights1`.
- Intended installer download URL: `https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.1.9-dashboard-insights1/Highlight_Desktop_Test_Setup_v1.1.9-dashboard-insights1.exe`.
- Latest repository checkpoint URL: `https://github.com/minhpark89/Highlight_Video_Studio/blob/release/v1.1.9/checkpoints/2026-10-04-dashboard-insights1.md`.

Build reproduction from a clean repository checkout uses `build_release.ps1 -Version 1.1.9 -PreviewRevision dashboard-insights1` with `-ToolSource`, `-IconSource` and `-WhisperModelSource` pointing to the user's existing installed tools/icon/model. Do not use local populated JSON ledgers as release seeds.
