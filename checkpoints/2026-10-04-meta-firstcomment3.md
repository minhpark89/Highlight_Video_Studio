# Highlight v1.1.8-meta-firstcomment3 — handoff

## Release identity

- Repository: `minhpark89/Highlight_Video_Studio`.
- Branch: `release/v1.1.8`; release tag: `v1.1.8-meta-firstcomment3`.
- Previous base commit: `c9ca1774dee1c43824466c59fd546bcb96b8863c`.
- The packaged `build_identity.json` records the exact source commit and clean/dirty state. The release checkpoint asset records the final commit, installer SHA-256 and download links.
- This is a desktop-test prerelease for operator testing. Existing releases are retained.

## Fixed in this revision

1. Installer normalizes archive names before deciding which files to preserve, including `./posts.json`. Existing post/history ledgers, credential/config data, package/profile/comment queues and render state survive updates. Mutable state is backed up before extraction.
2. `/api/content-studio/generate` now validates and forwards `article_url`. The UI accepts an optional existing Website URL. Without a URL, generation produces a draft; with a URL, the comment contains that URL exactly once. Enqueue reuses an existing URL instead of creating another CMS article.
3. First Comment component generation/retry retains origin, model, profile ID/name and fallback reason. Reusing an article/caption with a missing comment calls LLM first in auto/llm modes. Auto can use the selected niche template on LLM failure; explicit llm mode reports failure.
4. Already posted comments and frozen snapshots keep their text, state, source and profile when packages are reused, retried or fail. Changing a profile/default does not rewrite scheduled snapshots or Meta comments.
5. UI exposes separate comment metadata; native schedule labels are `Đã giao Meta`, `Meta đã đăng`, `Comment chờ xử lý`, `Meta từ chối`. App-held schedules show that the app must remain open. Historical Website failures are no longer labelled as LLM failures before LLM was called.
6. First Comment Studio layout and checkbox labels are fixed; duplicate Content Studio navigation was removed. Six builtin niches remain: police, sports, news, rescue, reality and general, each with 30 distinct templates.
7. Lazy Whisper CUDA/cuBLAS/cuDNN inference failures retry the entire transcription on CPU int8 and discard incomplete GPU output. Unrelated decoding failures and CPU failures are not retried automatically.
8. The render queue pause setting is persisted in `data/render_queue_state.json` and survives restart/update.

## Preserved guarantees from the prior revision

- Native Reel scheduling uses `video_state=SCHEDULED` and the >10 minute / <=29 day window. Verify Meta's scheduled publishing phase/time after finish. Persist upload identity before transfer/finish; never upload a second Reel after an ambiguous outcome.
- First Comment queue retains post ID, Meta video ID and exact token ID. It waits for independent publication verification; ambiguous comment outcomes require read-only reconciliation before retry.
- Group Page selectors/filter/select-all use the group's bindings. A missing/duplicate Vault ID blocks preflight before upload. Queued credentials remain immutable; token deletion is blocked while queued/processing posts depend on it.
- New Website images require three verified landscape frames from the original source/long video. AI hooks, YouTube thumbnails and portrait Reel frames are excluded. Missing or ambiguous clip metadata is rejected.
- Posts quiet refresh preserves rows; overdue minutes and worker state remain visible. No second scheduler was introduced.

## Verification completed before release

- Safe regression suite: **319 passed, 3 skipped, 29 subtests passed**.
- Release gates and inline JavaScript syntax passed; HTML mirrors are identical.
- Local actual installer extraction preserved 14 existing mutable files byte for byte; after restart the ledger remained **100 published / 100 comments posted**.
- Scheduler alive, last cycle OK, no overdue posts. Restored group health: 31/31 unique credentials, 100 bound Pages, no rebind required.
- The six incident Reels were independently read on Meta and each had exactly one comment containing its saved article URL. Four pre-upload failures were retried once; the two existing Reels were not uploaded again.
- Live UI generated a First Comment with the configured text LLM, containing the existing article URL exactly once. A temporary nondefault profile passed create/edit, LLM regeneration of 30 distinct samples and deterministic fallback, then was deleted. Default/profile snapshots and the post ledger remained unchanged.
- Live UI showed 100 rows, stable quiet refresh, token-group Page filtering, one Content Studio nav entry and no JavaScript exceptions.
- Required schedule labels were verified with browser-only fixtures; native scheduling behavior was verified by API mocks. No extra public Reel or schedule was created merely for testing.
- Installed runtime transcribed 12 seconds of real audio after the CUDA DLL failure by falling back to CPU; six transcript segments were produced.
- Final rebuild from the committed source must pass the release gates and payload/source checks before publication. Those checks are recorded in the release checkpoint asset.

## Remaining scope and permission boundaries

### Existing CMS article images

- Read-only review of 100 article items found 3 with valid landscape images and **97 requiring image repair**.
- 94 have three local replacement-frame previews from the matching original video. The other 3 use 1440x1080 (4:3) originals below the current aspect-ratio gate of 1.45; a source/crop decision is still required.
- Some published clips were already removed locally. The repair preview can use a unique preserved job/clip record to identify an existing original; the new publishing path still rejects missing clips.
- No historical CMS article PATCH/PUT or duplicate article creation was authorized/performed as part of this review. Obtain explicit operator confirmation after previewing the selected articles. Before an update, GET the current item/version/hash, preserve article ID/slug/embed/URL, and keep existing Meta Reels/comments unchanged.

### Historical local queues

- Render snapshot: 444 completed, 30 error, 29 queued, active/running=0, paused=true. The CUDA fix was verified with real audio; historical errors were not bulk retried and the paused batch was not resumed.
- Content Studio snapshot: 325 ready and 679 historical Website-failed packages with no linked post IDs. The UI now distinguishes these from actual LLM failures. Do not blindly retry them, because prior CMS creation may need reconciliation.
- The operator has not yet manually tested this release. Record new symptoms instead of treating the earlier automated checks as proof that every later environment will work.
- Do not modify Codex daemon/model configuration as part of Highlight recovery.

## Continue if the operator reports a bug

1. Read this checkpoint and the release checkpoint asset. Check `build_identity.json`, installer hash, branch/tag and the current runtime rather than assuming the previous port/PID/counts still apply.
2. Preserve `posts.json`, `posts.json.bak`, `posted_clips.json`, Vault, Page/group bindings, `jobs.json`, package/profile queues, pending comments and render pause state. Never print tokens/API keys/passwords or commit runtime data.
3. Inspect the affected original post/job/package IDs and the failure stage. If an upload/video/comment ID exists or outcome is unknown, reconcile Meta read-only first. Never republish an already published Reel or rerun completed credential migration scripts.
4. Capture the selected safe error/status fields, reproduce using an existing article URL or mocks, add a regression for the observed failure, then fix the owning layer.
5. For First Comment, check mode, article URL, task/main model availability, quota circuit and fallback reason separately. For an old comment whose origin was not persisted, keep the UI uncertainty; do not fabricate historical provenance or edit the Meta comment.
6. Run affected tests and the required release gates. Restart/install only when Meta publishing/processing and render active/running are zero; preserve the operator's pause choice.
7. Build a new revision/tag for a subsequent fix, publish its installer/hash/checkpoint, and verify the GitHub asset digest. Do not overwrite an already published revision.

## Commands and files

```powershell
cd E:\OPENCLAW\BOB\source-worktree
git status --short
git show v1.1.8-meta-firstcomment3 --stat
python -m pytest tests -q --no-header
.\build_release.ps1 -Version 1.1.8 -PreviewRevision meta-firstcomment3 `
  -ToolSource 'E:\OPENCLAW\BOB\Highlight destop test\bin' `
  -IconSource 'E:\OPENCLAW\BOB\Highlight destop test\app.ico' `
  -WhisperModelSource 'E:\OPENCLAW\BOB\Highlight destop test\models\faster-whisper-small'
```

- Installer preservation: `Installer.cs`, `tests/test_installer_data_preservation.py`.
- Content generation/snapshots: `src/content_packages.py`, `web/app.py`, `tests/test_first_comment_audit.py`.
- Model routing/fallback: `src/publisher/website_publisher.py`, `src/first_comment_profiles.py`, `src/fallback_comments.py`.
- Whisper inference: `src/pipeline.py`, `tests/test_whisper_lazy_fallback.py`.
- UI mirrors: `web/templates/index.html`, `web/index.html`.
- Native handoff/credential tests: `tests/test_meta_native_handoff.py`, `tests/test_meta_scheduling_profiles.py`, `tests/test_page_token_sync.py`.
- Provenance tests: `tests/test_preview23_image_sources.py`, `tests/test_preview26_source_metadata.py`, `tests/test_preview28_long_article_fallback.py`.
- Read-only CMS audit: `ops/audit_article_images.py`.

On the original workspace, `E:\OPENCLAW\BOB\CODEX_CHECKPOINT_LATEST.md` also records local runtime/evidence/backup locations after cleanup. Private backup/credential material must never be attached to a GitHub release.
