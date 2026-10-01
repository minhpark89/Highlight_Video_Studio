# Highlight Video Studio — Preview 24 checkpoint / session handoff (2026-10-01, GMT+7)

## User request and current verdict
- Boss will download and test Preview 24 on another PC. If the app still fails, the next session must investigate and perform a bounded **real Meta publish test** to verify the fix, with the boss's explicit authorization in this conversation (2026-10-01 00:15, reiterated 07:03). Do not claim the publish problem is solved from offline tests alone.
- As of 07:56 GMT+7, **no Preview 24 live post has been attempted or verified**. No new Reel ID / independent Meta GET / comment / CMS / ledger receipt exists. Installed PC listener on port 56570 was still the older Preview 4 isolated build; Python listeners 5070/5080 were older processes. Do not test an old listener and attribute its outcome to Preview 24.
- Do not auto-retry the two older `scheduled` posts from the boss's `posts.json` attachment (23:53 and 23:57 on Sep 30). They lack a Facebook object ID and their clip basenames are absent from the supplied `posted_clips.json`, but that does **not** prove Meta did not publish them. Reconcile against the corresponding Pages on Meta first.

## Release / immutable identity
- GitHub release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.0.19-desktop-test.24
- Installer: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.0.19-desktop-test.24/Highlight_Desktop_Test_Setup_v1.0.19-preview.24.exe
- Checksum attachment: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.0.19-desktop-test.24/Highlight_Desktop_Test_Setup_v1.0.19-preview.24.sha256
- Source branch `fix/v1.0.19-content-studio-font-image`; release tag `v1.0.19-desktop-test.24` points to `cd9f9e2` (full hash: inspect Git). Earlier fix commit `5e5d845` and release hardening `cd9f9e2`. Local installer observed 680,605,184 bytes, SHA-256 `A04A3E460F86D63C1F29FD3FF05DD36BCF559279055FA611566139E192E75506`. Preserve Preview 23 tag `v1.0.19-desktop-test.23` and its installer; do not repoint immutable tags or silently replace assets.
- Checkout for source and build artifacts: `F:\openclaw\.openclaw\workspace\worktrees\preview23-fix-20261001`. Installed user/runtime data are NOT part of the installer. Do not bundle tokens, posts, cookies, or output clips.

## User-reported issues and evidence level
1. **Two posts vs `posted_clips.json`:** Fixed confirmation-versus-ledger reconciliation; avoid declaring a confirmed Meta post unposted merely because the local ledger lags. Both attached posts were `scheduled`, not independently verified on Meta. No live proof of fix yet.
2. **9router image endpoint:** Selected-model connection probe adjusted; offline coverage only. No authenticated image generation from the installed app verified yet. Test the configured endpoint/model safely without displaying credentials.
3. **Content Studio failed articles:** Failed-only select-all and queued LLM regeneration added; repeat/manual selection does not trigger a real publish. UI and API offline tests only.
4. **Non-LLM images:** Use horizontal frames / YouTube thumbnail fallback from original long-form source, rather than vertical short-clip frames, for thumbnail and article images. Offline tests only; inspect actual rendered article on PC.
- Release evidence reported: 115 focused tests and release groups 42 + 25 + 49 + 38 passed. These are mocked/offline, **not** a live Meta/CMS/image test.

## PC data/runtime map (read-only findings; recheck when resuming)
- `D:\Highlight_Video_Studio` held 100 locally VERIFIED Page–Token fingerprints, 345 output MP4s, and 241 substantial candidates absent from the then-known posted/active queue; one candidate passed ffprobe. This is not an online token validity check. This checkout is dirty with substantial prior user edits; never overwrite whole tree or reset it.
- `D:\Highlight_Video_Studio_v1015` had two output MP4s but no usable verified Page–Token mappings. Directory name/version labels alone do not establish the serving build.
- Fixed worktree had zero mapped Pages and zero output MP4s. Its `HIGHLIGHT_DATA_ROOT` guard rejects redirecting it to the D: installation; do **not** bypass the guard or copy private data into Git simply to publish.
- A preflight artifact exists locally at `artifacts/preview23_real_post_preflight_20261001.md` (untracked runtime note). No real-post receipt as of this checkpoint.
- Working-tree runtime state may be dirty (`posts.json`, `data/content_packages.json`, `data/run/`, `run/`). Never stage/commit it or treat it as proof of published status.

## Next-session mandatory sequence if boss reports failure
1. Read this file and `CHECKPOINT_PREVIEW23_SESSION_RESET_20260930.md`, user failure details, exact installed Preview 24 `build_identity.json`, listener executable/process/cwd, and app-owned data root. Compare source/payload hashes and app version with release tag before any live test. Identify the ONE intended instance; do not create another checkout/install, stop unrelated apps, or clobber existing data.
2. Reproduce the failure with redacted local logs and a minimal offline test, fix in source if necessary, then build a **new** preview number after checking tags/releases. Do not rewrite Preview 24. For image failure, verify configured 9router model/endpoint and one authenticated image request through the app without exposing key material. For Content Studio, verify select-all/requeue and horizontal article imagery.
3. For publishing, verify a current exact Page–Token binding online, an eligible new video not in published/queued ledgers, no outstanding ambiguous result for that video, app's own data path, and that the exact fixed build is serving. Establish the applicable publishing owner/approval boundary for Highlight's **direct Meta** flow rather than automatically importing Shared Video Ops render-worker `mayPublish:false`; if a current owner-matched packet/publish gate actually applies, honor it and obtain the proper route, never bypass it. Boss's authorization is for a bounded new real test post; no blanket bulk publish.
4. Publish **at most one fresh post** through the correctly identified fixed app. Record redacted post/job ID, Page ID, time, returned Reel/object ID. Independently Meta GET that object and verify visibility/status, first comment and CMS article if configured, and reconcile `posts.json` plus `posted_clips.json` without leaking access tokens. On ambiguous finish/no object ID, STOP and reconcile remotely; do not retry blindly or mark success.
5. Report explicitly which of Meta post, first comment, CMS, image endpoint, UI, and ledger passed or failed, with redacted evidence. If a real-post gate or token/service blocks the test, report the exact blocker; do not assert production readiness.

## Boundaries
- Publishing/scheduling rules for the separate MXH Python Service (Zernio-only) do **not** apply to Highlight Studio, which uses direct Meta Graph API.
- Do not disclose credentials, token text, secret config, or copy live runtime data into repository/release. Preserve boss's Chrome/processes and the two older posts until reconciled.
- Boss requested checkpoint and will test Preview 24 first. Do not initiate a real post merely to satisfy this checkpoint turn; resume when boss returns with test outcome.
