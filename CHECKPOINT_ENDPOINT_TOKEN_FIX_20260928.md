# CHECKPOINT — Endpoint ảnh + Page token — 2026-09-28 09:54 GMT+7

## User request
Fix triệt để two defects reproduced on a second PC in both v1.0.19 and Desktop TEST:
1. 9router image generation endpoint works externally but not in app. Generation URL and model-list URL must remain independent; real image model must replace `__video_frame__` when AI image is intended; runtime must accept URL/Base64/nested chat image responses.
2. Add token modal: after naming token, `Lưu & Đồng bộ Page` did nothing. Fix frontend handler/button wiring, API response, TokenVault/Page synchronization, and visible loading/success/error feedback.

## Canonical development location
- Worktree: `F:\openclaw\.openclaw\workspace\worktrees\highlight-multi-pc`
- Branch: `feature/multi-pc-control-plane`
- Production `D:\Highlight_Video_Studio` on port 5080 must not be changed/restarted during development.

## Current uncommitted implementation in worktree
- `web/templates/index.html` + `web/index.html`: added `submitAddToken()`, wired `btn-submit-token`, loading/error/success behavior, POST `/api/tokens`, refresh token and page state, close modal.
- Model lookup now promotes first real model over `__video_frame__`.
- `src/publisher/page_manager.py`: syncs `token_name`, `token_id`, `page_token`.
- `web/app.py`: image test supports dedicated generation/models URLs and detects URL/Base64/nested chat output.
- Regression tests added to `tests/test_page_token_sync.py` and `tests/test_release_guards.py`.
- Source and packaged templates currently byte-identical; inline JS passed `node --check`.

## Verified so far
Command:
`python -m pytest -q tests/test_page_token_sync.py tests/test_release_guards.py tests/test_multi_pc_local_mvp.py tests/test_multi_pc_hardware.py tests/test_multi_pc_phase1.py`
Result: **87 passed in 8.74s**.

## Remaining work
1. Inspect `git status`/`git diff`; preserve uncommitted fixes.
2. Review and test actual runtime generation in `src/publisher/website_publisher.py` so it shares response handling behavior with `/api/image-provider/test`.
3. Add missing runtime regression tests, then run targeted + broader relevant suite.
4. Perform safe manual canary without exposing secrets.
5. Build new Full Offline preview installer, install cleanly on isolated path, launch loopback ephemeral, verify both flows, ensure production port 5080 remains healthy.
6. Commit. Publish only a TEST pre-release/update domain latest after all verification; do not publish production release.

## Safety
Never print/commit API keys or Facebook tokens. Do not modify tracked config with machine-specific secrets/profile. Keep backend loopback-only. Do not touch production instance until explicit rollout approval.
