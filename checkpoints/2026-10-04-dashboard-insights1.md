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
