# Highlight 1.1.8-meta-handoff4 — 04/10/2026

## Behavior

- Existing app-held schedules can be handed to Meta from Quản lý Bài Đăng, individually, by selection, or with the all-eligible button. Summary counts and state filters distinguish app schedules, sending/verification, Meta schedules, published posts, and failures.
- App schedules explicitly say the video has not reached Meta and the app must run at publish time. Only verified native schedules say Meta holds the schedule and can publish video while the app is closed.
- First Comment still requires the app after independently verified publication. Native schedule selection explains this separately.
- `POST /api/posts/handoff-meta` queues existing rows without uploading in the request or creating new post IDs. The existing scheduler sends one handoff per cycle and runs faster while more handoffs are queued; due app posts and comments retain priority.
- Eligibility requires an app-held untouched schedule, more than 10 minutes and at most 29 days away, a ready Website and frozen comment with exactly one URL, a local video, and the original verified Page credential. Recheck immediately before upload.
- Original post ID, Page, token ID, video, caption, time and comment provenance/snapshot stay intact. Persist the upload ID before transfer/finish. Uncertain outcomes remain processing and use existing read-only reconciliation, never another upload.
- A definitive failure before upload or an expired handoff window leaves the original app schedule intact. Local deletion/clear cannot erase a handoff, processing post or Meta-held schedule and pretend to cancel its external schedule.

## Validation and artifact

- Full safe suite: 335 passed, 3 skipped, 29 subtests. New queue handoff suite: 16 passed. Existing build release gates also pass, including the new suite.
- Browser fixtures cover 200 rows, selection and quiet row preservation, single/bulk transfer, summary counts, native schedule + comment labels, state/empty filters, and 1600/1280 px layouts. No page errors. Fixture write requests are intercepted; no public Meta schedule is created for QA.
- Revision: 1.1.8-meta-handoff4. The installer build identity records the exact clean source commit; inspect the final payload report and SHA-256 file for artifact identity.
- Local installer: `release/Highlight_Desktop_Test_Setup_v1.1.8-meta-handoff4.exe`.
- Supporting browser evidence: `E:/OPENCLAW/BOB/support/meta-handoff4/evidence/`.

## Live state and continuation

- Installed app was still meta-firstcomment3 at the time of this change. The new installer has not been applied while publishing/rendering is active; do not interrupt a real upload or render to install it.
- At task start, live ledger held 100 published and 100 new app schedules, all Website/comment/video ready. Their original times were 11:30–12:15 on 04/10/2026. The existing scheduler continues publishing naturally while this work runs; counts must be read again, never inferred from the initial snapshot.
- No operator schedules have been automatically handed to Meta by this task. The operator can select eligible schedules in the updated UI. Expired/near-due schedules remain with the app.
- No old CMS content, credentials, bindings, comment snapshots, Meta IDs or render pause choice were edited. Private backups remain private.
- Refer to root `CODEX_CHECKPOINT_LATEST.md` for current runtime observations and verified installer metadata. Read process/port, publishing/processing and render activity again before applying the new installer.
