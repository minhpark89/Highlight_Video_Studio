# Highlight 1.1.9 — Meta schedules, parallel publishing and Token/Page groups

> Installed and verified on 2026-10-04 after the operator confirmed deployment following the Meta audit. Runtime: `http://127.0.0.1:61989`. Packaged source: `e4723a2`; installer SHA-256: `fce46899de12cacce3538e350cbcc3f492d815c229b7baec072ecf3e95fd4a92`. Earlier deployment holds in this document are historical; the final sections record the completed installation and live verification.

The app supports 1, 2, 4 or 8 publishing workers (default 4, maximum 8). The setting is persisted independently of render concurrency and is exposed in Token Management, Post Management and both scheduling dialogs. Due app posts and queued Meta handoffs run in parallel across distinct credentials; each Token/Page has at most one active upload. Per-token spacing and Meta usage/cooldown gates remain enabled.

Workers load an independent posts-store revision, persist upload identity before transfer/finish, and merge only changed fields. Shared clips are removed only after every queued Page has confirmed publication. Queue/history, First Comments and concurrent Content Studio metadata are preserved.

Scheduling dialogs expose App-held and Meta-held modes before confirmation. Batch Meta mode prepares Website/First Comment content before requesting a handoff. If its native scheduling window expires, the app reports a failure and asks for a new schedule instead of silently posting through the app. First Comment still requires the app after the scheduled publication time.

Token groups refresh immediately after creation. Token import can choose an existing group or create a named group; ungrouped tokens are labelled explicitly. Creation synchronizes each selected credential independently, snapshots Pages from a chosen source or the verified pool, and can create a linked Page group. Group allocation persists one verified credential per Page in `page_token_bindings`; new posts honor that assignment even when another group changes the Page's default credential. Existing queued credentials are never rebound. Page filters use group Page snapshots and management dialogs fetch current lists/counts.

Verification: Python compilation, the complete regression suite, and an isolated browser smoke test covering fresh groups, linked Page selectors, saved worker counts and both batch modes. Browser network was intercepted; no test uploaded a real Reel or changed live credentials. Detailed evidence is kept under `E:\OPENCLAW\BOB\support\meta-token-groups1\evidence`.

Deployment uses the actual installer extraction/preservation code, only when Meta publishing/processing and render active/running are zero. Preserve queue, Vault, Pages/groups, content packages, comments, profiles, config and render pause state. Do not resume paused render jobs or convert existing app schedules.

Release/deployment identities and final verification are appended after packaging and installation. The previous release and private backups remain available.

Slow Meta processing continues to be checked read-only after six attempts, with a five-minute interval. A confirmed upload is never replayed. This addresses the observed `upload_complete` / `processing not_started` object that the previous runtime stopped checking after attempt six.

## Final verified installer and deployment hold - 2026-10-04

- Branch: `release/v1.1.9`; clean source commit: `e4723a25c14aec0dbc56ebc84c22381c44c8c03a` (includes read-only reconciliation beyond six checks).
- Installer: `E:/OPENCLAW/BOB/source-worktree/release/Highlight_Desktop_Test_Setup_v1.1.9-meta-token-groups1.exe`.
- Final installer SHA-256: `fce46899de12cacce3538e350cbcc3f492d815c229b7baec072ecf3e95fd4a92`; size: 703367168 bytes. This replaces the earlier local build hash; no GitHub publication was performed for this revision.
- `support/meta-token-groups1/tools/verify_release.ps1` passed on the final build: 7886 archive entries, empty post/credential seeds, no runtime state, all tested module hashes match, HTML mirrors match, clean build identity.
- Earlier full regression result: **352 passed, 3 skipped, 29 subtests passed**; isolated browser smoke passed without JavaScript errors. Verification was not repeated unnecessarily after the already tested build.
- Running app remains v1.1.8 at `http://127.0.0.1:56051`; installer has NOT been applied and runtime has NOT been restarted.
- Latest saved live snapshot: `2026-10-04T13:21:06.761853` (Asia/Saigon): **1 processing, 199 published**, 200 total/unique post IDs. Render remains paused with active=0 and running=0; scheduler alive, cycle active=False, last cycle OK.
- Processing post `post_1791087110_aaee5d` retains Meta object `1107514081727419` and reconcile_attempts=6. Earlier read-only Meta check reported upload_complete with processing/publishing not_started. Never replay its upload.
- Pending operator choice: keep waiting until processing clears, or explicitly allow installation after uploads finish while preserving the processing IDs so 1.1.9 can continue read-only checks. No answer has been received; do not treat the pending question or elapsed time as authorization.
- Existing `install_when_idle.ps1` strictly blocks on publishing/processing/meta_handoff, active render work or an active scheduler cycle. Do not run it while any blocking activity exists. If the operator explicitly chooses installation with processing IDs preserved, first adjust the helper to accept only durable IDs with completed transfer and no active uploads, preserve/verify mutable data and pause state, then apply and verify the new runtime.
- Evidence: `support/meta-token-groups1/evidence/payload_verify.json`, `ui_smoke.json`, `processing_audit.json`, and `pre_install_status.json`.

## Deployment preflight prepared - 2026-10-04T13:26 (Asia/Saigon)

- A fresh independent Graph GET verified `1107514081727419` still exists, has upload_complete and 61094086 bytes transferred, processing/publishing not_started, no published Reel permalink. Exact original credential/Page binding was verified locally before the GET. No remote write, local queue mutation, or upload retry was performed.
- Evidence: `support/meta-token-groups1/evidence/processing_audit_latest.json`; helper: `support/meta-token-groups1/tools/check_processing_readonly.py`.
- Installation helper now has explicit `-AllowDurableProcessing` and safe `-PlanOnly` parameters. Its default still blocks on processing. The exception requires a fresh Meta GET for the existing durable object ID and exact credential, zero publishing/handoff activity, an idle scheduler, and paused/idle rendering. Existing installer backup/hash-preservation checks remain in place.
- `install_when_idle.ps1 -AllowDurableProcessing -PlanOnly` passed: 199 published, 1 processing, 200 total, no active uploads/rendering, retained `post_1791087110_aaee5d`. `-PlanOnly` without the exception returned runtime_busy as required. Neither invocation installed or restarted the app.
- Concrete reviewed plan: after an explicit operator choice to install while preserving the processing object, invoke `powershell -ExecutionPolicy Bypass -File .\support\meta-token-groups1\tools\install_when_idle.ps1 -AllowDurableProcessing`, then verify mutable ledgers/hash preservation, runtime build identity, new worker settings, group UI and both scheduling modes. Keep render paused.
- The pending operator choice remains unanswered. Automatic goal continuation does not select an option or authorize the checkpoint exception. Deployment remains incomplete while this choice or a verified change in Meta publication state is pending.
- This is the third consecutive goal turn with the same deployment condition unresolved (the handoff turn, the checkpoint/verification turn, and this fresh preflight turn). All independently useful deployment preparation is complete; request blocked status rather than continue repeating this wait.

## Deployment completed - 2026-10-04T13:34 (Asia/Saigon)

- User confirmed: check the outstanding Meta object, then deploy. A fresh read-only Graph GET immediately before installation found `post_1791087110_aaee5d` / Meta object `1107514081727419` with `upload_complete`, 61094086 bytes transferred, `processing_phase=not_started`, `publishing_phase=not_started`, no error and no published permalink. Exact Page/token binding was verified. No upload or Meta write was repeated.
- Installed with the actual extraction/preservation path and the explicit durable-processing exception. Installer SHA-256: `fce46899de12cacce3538e350cbcc3f492d815c229b7baec072ecf3e95fd4a92`; source commit: `e4723a25c14aec0dbc56ebc84c22381c44c8c03a`; build identity: `1.1.9-meta-token-groups1`.
- Preservation report: `support/meta-token-groups1/evidence/install_preservation.json`; `installed=true`, 21 mutable files checked, `mutable_hashes_unchanged=true`, `code_hashes_match=true`, render pause retained. The outstanding post and Meta upload ID remain in `posts.json`.
- Runtime: `http://127.0.0.1:61989`; `/api/system/info` reports app version `1.1.9`. The scheduler is alive with `last_cycle_ok=true`, `cycle_active=false`, `active_posts=0`, and no overdue posts. Render remains `is_paused=true`, `active=0`, `running=0`.
- Post ledger after restart: 200 total and 200 unique IDs; 199 `published`, 1 `processing`; 199 First Comments posted and 1 ready. The new runtime has already advanced the slow post to read-only reconcile attempt 7 and retained its Meta ID; it did not re-upload.
- Publishing settings: `posting_threads=4`, `max_posting_threads=8`. Page mapping health: 130 total, 130 verified, 0 unhealthy, 32 mapped credentials. Token group `NEW` has 31 tokens and 100 Pages; Page group `NEW` has 100 Pages.
- Live browser verification: `support/meta-token-groups1/evidence/runtime_ui_verify.json` and `runtime_ui_verify.png`; no page errors, 4 worker selectors load value 4, both App-held/Meta-held delivery modes are present, Page group filters and Manage Groups modal show `NEW`.
- Runtime evidence: `support/meta-token-groups1/evidence/runtime_verify.json`; Meta audit: `processing_audit_latest.json`. Previous release and all mutable data remain preserved. The deployment objective is complete; continue read-only reconciliation of the remaining Meta object and never replay its upload.

## Post-deployment verification - 2026-10-04T13:40 (Asia/Saigon)

- Final runtime snapshot: `support/meta-token-groups1/evidence/runtime_verify_final.json`. App `1.1.9` is live at `http://127.0.0.1:61989`; scheduler alive/healthy, render paused and idle, 199 published + 1 processing, 200 unique post IDs.
- Slow Meta object `1107514081727419` remains linked to `post_1791087110_aaee5d`; the new worker has performed read-only reconcile attempt 8. Its upload ID remains unchanged.
- Token/Page verification: 130/130 Pages verified, 0 unhealthy, 32 distinct assigned credentials, 130/130 Page records with `token_bindings`; Token group `NEW` = 31 Tokens/100 Pages and Page group `NEW` = 100 Pages.
- Live UI evidence: `support/meta-token-groups1/evidence/runtime_ui_verify.json`, `runtime_token_group.png`, and `runtime_schedule_modes.png`. No JavaScript errors; worker selector options are 1/2/4/8 and persisted value 4; Token group management, Page group filters, and both App-held/Meta-held scheduling modes were exercised read-only. Temporary setting change to 2 was restored to 4.
