# Checkpoint / Handoff — Preview 18 (2026-09-30)

## Canonical repository state
- Repository: `minhpark89/Highlight_Video_Studio`
- Local path: `F:\openclaw\workspace\highlight-studio-test15-fix`
- Branch: `fix/v1.0.19-content-studio-font-image`
- Code fix commit: `fe5af08a8a71cf093d0cb66fcd19d4d9d0a9e905` — `Fix content package status and scheduled publishing`
- Preview checkpoint commit: `3c966de4793acd21856d166b44be0b4c9715ab3f` — `Add preview.18 release checkpoint`
- Preview 18 release tag: `v1.0.19-desktop-test.18` (annotated tag object `2c74172e747d456ec9522f1de312d123b4acdd30`, resolves to commit `3c966de4793acd21856d166b44be0b4c9715ab3f`)
- At checkpoint creation, the branch and tag were pushed to `origin`; release is online.

## User request / expected continuation
Boss asked to checkpoint so a fresh session can continue if new bugs are reported. Start from this branch and read this handoff plus `CHECKPOINT_PREVIEW18_20260930.md`. If boss reports a new issue, reproduce it against preview.18, make a targeted fix and regression test, run the smallest relevant tests first, build a new incremented preview (do not overwrite/repoint preview.18), verify the installer payload identity/source and release download/checksum, then report a direct download link.

## Preview 18 fixes
- Content Studio queue shows per-component status for hero title, article, first comment, and website URL.
- Folder batch compares clip paths/basenames to posted-clips history and existing queue items; already-posted/already-queued clips are skipped.
- Content package worker resolves the CMS article URL before generating/persisting first comment, so the comment can contain that exact URL.
- Scheduler holds due scheduled posts while linked content package state is `queued` or `running`; next cycle rechecks after generation.
- UI templates `web/index.html` and `web/templates/index.html` synchronized.
- Regression cases added in `tests/test_scheduling_publish_flow.py`.

## Verification evidence
- Targeted test run after checkout: `python -m pytest tests/test_scheduling_publish_flow.py tests/test_release_guards.py -q --no-header` → **52 passed**.
- Release build script run: `build_release.ps1 -Version 1.0.19 -PreviewRevision preview.18 -BuildChannel desktop-test`; all script test groups passed in that build run (42 + 25 + 44 + 30 tests); packaging guard reported clean.
- Important release-gate correction: initially existing local preview.18 installer had identity `fe5af08` whereas current checkpoint HEAD was `3c966de`. The installer was rebuilt from HEAD before publication. Do not use the initial artifact/hash; it was overwritten by the verified rebuild.
- Verified installer embedded `build_identity.json`: source commit `3c966de4793acd21856d166b44be0b4c9715ab3f`, prerelease `1.0.19-preview.18`, desktop-test, loopback-only. Embedded `src/content_packages.py` matches committed source after CRLF normalization.
- Installer: `release/Highlight_Desktop_Test_Setup_v1.0.19-preview.18.exe`; size **680,583,680 bytes**; SHA-256 `49e257fef631bb3fb4750643dd204a087458dfed7c62566ae51e687de1314205`.
- GitHub release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.0.19-desktop-test.18
- Direct installer: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.0.19-desktop-test.18/Highlight_Desktop_Test_Setup_v1.0.19-preview.18.exe
- Checksum asset: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.0.19-desktop-test.18/Highlight_Desktop_Test_Setup_v1.0.19-preview.18.sha256
- Release metadata confirms both named assets uploaded with expected sizes/digests. Direct URL HEAD returned HTTP 200 and expected 680583680-byte length. Installer was fully downloaded and SHA-256 matched local file.
- Preview.18 is side-by-side desktop-test build, `127.0.0.1`, ephemeral port; installer source reviewed for separate `Highlight Desktop Test` product/registry/shortcuts and process stop scoped to processes located under selected test install directory.

## Important implementation/context notes for future bug fixing
- Project root is `F:\openclaw\workspace\highlight-studio-test15-fix`.
- Build script: `build_release.ps1`; installer artifact under `release/`.
- Test runner is Python on this Windows host; use the repository's documented test approach.
- `src/content_packages.py` uses `DATA_ROOT = canonical_data_root()` and persisted queue at `data/content_packages.json` under canonical data root.
- Scheduler file is `web/scheduled_publisher.py`.
- Working tree was cleaned after tests; test-generated `posts.json`, `data/content_packages.json`, `data/run/...lease`, and `run/...lease` were removed/restored. Check status before new changes.
- Do not publish to social platforms during testing; no such approval was given. GitHub release upload was explicitly requested as app deployment/download.

## Previous handoff
`CHECKPOINT_PREVIEW18_20260930.md` documents the prior code/release checkpoint; `CHECKPOINT_PREVIEW17_20260930.md` documents the original report context. Continue from the current branch head rather than older handoff commit references.

## Hotfix follow-up — Preview 19 (2026-09-30)
- User reported app stayed on Research and all tabs were unresponsive after opening preview.18.
- Root cause in `web/index.html` and `web/templates/index.html`: Content Studio queue renderer's returned `<tr>` template literal lacked its closing backtick before `.join('')`. This caused the browser to reject the entire inline JavaScript block, disabling all tab navigation.
- Fixed the boundary and added regression assertion in `tests/test_website_ui_regression.py`.
- Both page scripts now parse with Node `new Function(...)`; focused UI/release tests: `31 passed`.
- Release build completed with all build suites passing: 42 + 25 + 44 + 30 tests. Packaging guard passed.
- Hotfix source commit: `25728b27445b5f1058f53d5bed81ec2853f02b4b`.
- Preview.19 tag: `v1.0.19-desktop-test.19`, verified to resolve to that exact hotfix commit.
- GitHub release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.0.19-desktop-test.19
- Installer URL: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.0.19-desktop-test.19/Highlight_Desktop_Test_Setup_v1.0.19-preview.19.exe
- Asset size: 680,583,168 bytes. Local SHA-256: `0fcb0ae9353549ae20a7a0919945c173e448e8ab593bda204ddd48226fc065a5`.
- GitHub release API reports explicit uploaded installer and `.sha256` assets; installer API digest equals local SHA-256; exact download endpoint HEAD returned HTTP 200. A full local re-download attempt was interrupted/incomplete (partial temporary file had mismatched length/hash), so do not claim a completed round-trip download for preview.19. GitHub's reported asset digest and size match the local installer.
- Build identity is generated by `build_release.ps1` from source commit at build time. Do not overwrite preview.19; next fix should use preview.20.
