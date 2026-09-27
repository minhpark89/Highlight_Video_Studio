# Highlight Video Studio v1.0.18

## Page / Token / Token-Group / Sync fixes

- **Removed duplicate/stale JS handlers** in `web/templates/index.html`. Multiple top-level
  definitions of the same function shadowed each other, so the last (stale) definition won:
  - `openAddGroupModal` / `closeAddGroupModal` — the stale stub replaced the live
    implementation (which populates the Fanpage selection list), leaving the "Add group"
    modal blank/broken.
  - `openScheduleRulesModal` / `closeScheduleRulesModal` — the stale stub replaced the live
    implementation that also refreshes the rules config from `/api/schedule/rules`.
  - `executeBatchDistribute` — the stale copy referenced DOM ids that no longer exist
    (`dist-select-group`, `dist-start-time`, `dist-stagger`, `dist-result-banner`,
    `btn-batch-distribute`) and shadowed the working handler, breaking the
    "Bắt đầu Tự động Phân bổ & Lên lịch" button.
- **Group filter now uses the real backend schema.** `renderFilteredPages()` keys off
  `group_ids[]` / `group_id` / `group_name` instead of the non-existent `p.groups` array,
  so filtering the Pages view by Fanpage group actually returns the right pages.
- **Group-name display** no longer depends on `p.groups[0]`; it uses `group_name` with a
  safe default.
- **Schedule-rules / distribution config** now reads the Fanpage group list and inputs from
  the current endpoints and element ids (`/api/groups`, `modal-dist-group`,
  `modal-dist-starttime`) instead of the removed `/api/pages/groups` route and stale ids.
  A 404 on `/api/pages/groups` no longer aborts the distribution card setup.
- **Single-page token assignment** (`openAssignSingleTokenModal`) now posts `token_id` (the
  field `/api/pages/assign_token` expects) and checks HTTP status, so the value the user
  typed is actually persisted as the page binding instead of silently failing.
- **Token / page sync schema** verified end-to-end: adding a token syncs pages with
  `page_id` + `group_ids` + `token_id`; token list stays masked (no raw token returned).

## Carried over from v1.0.17 (image endpoint)

- Separate `Endpoint tạo ảnh` vs `Endpoint lấy model` per provider; `/models` is optional
  and a 404 no longer blocks entry.
- Image test uses the exact URL the user entered and picks the payload shape for
  `/images/generations` or `/chat/completions`.
- Backward compatible with v1.0.16 config (`api_base` alone infers an OpenAI-compatible
  endpoint); `__video_frame__` still extracts a video frame instead of calling image AI.

## Verification

- `python -m pytest tests -q` — 39 passed (includes new `tests/test_page_token_sync.py`:
  frontend invariants for duplicate handlers / stale DOM ids / real routes, plus backend
  API tests for token add+sync, groups CRUD, page binding, single/batch token assign and
  token-group CRUD).
- Runtime files deployed to `D:\Highlight_Video_Studio` with timestamped backups; only
  `web/index.html` and `web/templates/index.html` replaced — user config, tokens,
  schedules and media untouched.
- Service on port 5080 restarted and verified HTTP 200 plus smoke tests: `/api/groups`,
  `/api/pages`, `/api/tokens`, `/api/token-groups`, `/api/clips`, `/api/jobs`, `/api/posts`,
  `/api/schedule/rules`, `/api/system/info`, `/api/queue/status` all 200; served HTML has
  exactly one definition of each fixed handler and no stale id references; `/api/tokens`
  returns masked entries only.
