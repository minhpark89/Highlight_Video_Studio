# Content Studio 1 — 2026-10-04

Revision: `1.1.9-content-studio1`, branch `release/v1.1.9`.

## Completed implementation

The Website video diagnostic now tests the route actually used by CMS articles: authenticated CMS access plus embedding the original YouTube video. The UI explains that the CMS uploads images and SCP stores MP4 files for sources without YouTube. A CMS connection is not presented as support for uploading MP4 to its image endpoint.

Content Studio prefers the configured text LLM and requests a 750–950 word article with one sentence per paragraph. Auto mode uses a long viewing guide based on the supplied title, source description and niche when the LLM fails. Required-LLM mode retains an explicit failure. The fallback does not invent events, quotes or outcomes. The selected niche accepts free text, including custom profile niches.

Fallback First Comments use 30 distinct lead-ins. Rotation persists digest/index selections in `data/first_comment_rotation.json`; retries for the same title/URL/profile retain their selection. The deterministic option remains available. The selected option is honored by quick generation and queued work, and batch submission passes the selected profile. Existing scheduled or posted comment snapshots retain their original text.

Content Studio supports 1–4 concurrent videos, default 2. Its background worker holds an exclusive process lease, claims queue rows atomically, and fences concurrent work for the same clip. Active titles, clip filenames and processing stages appear in the queue. Starting the queue returns HTTP 202 immediately. `run_server.py` starts the worker on app startup. Interrupted CMS generation requires an explicit retry after checking the existing article; the stable slug/embed check prevents a duplicate CMS POST.

The CMS pipeline generates one content package while image preparation runs concurrently. Its exact article HTML is rendered and saved back to the queue, with a hero image, two original landscape frames and the full player at the end. The configured image model gets priority for the hero; source frames remain the fallback. Square model output is preserved on a 1280×720 canvas. Parallel image generation writes unique temporary files before atomically replacing a validated cache image.

Post Management shows token display name, original Token ID, configured Page count, group-assigned Page count, Pages with posts and published/pending/failed totals. Its token table expands Page IDs/names and filters posts by original Token ID. Duplicate operator names use Meta owner names where available. Missing/deleted original tokens and changed assignments stay visible. The API never substitutes current assignments for a post's original Token ID, and raw posting credential fields are excluded from `/api/posts` responses.

## Validation

- Full offline suite: **398 passed, 3 skipped, 29 subtests passed**.
- Release gate groups passed, including scheduler, YouTube embeds, token mapping, installer data preservation and Content Studio.
- Python compilation passed; `web/index.html` and `web/templates/index.html` are byte-identical.
- Browser smoke at 1600/1280 pixels: no JavaScript errors; niche/profile/rotation payloads, active clip/stage, worker selection, token names/IDs/counts/filter and Website diagnostic passed.
- Existing provider probe: configured text model `ag/gemini-3.6-flash-high` produced a 760-word article; authenticated CMS connection succeeded. The initial combined probe rejected square image output before normalization was implemented. The subsequent image probe returned HTTP 200 and a valid normalized 1280×720 JPEG from `ag/gemini-3.1-flash-image`.
- Read-only runtime audit contained 200 posts and 41 tokens. There were zero Meta write calls and zero test CMS articles published. Production article publication was exercised with isolated mocks, not a live test article.

`tests/conftest.py` isolates Content Studio queue/circuit/data paths for every test and prevents the three continuous render/publish/content loops from starting during pytest. Actual concurrency threads/executors still run. This fixes the previously intermittent suite failures caused by background workers using another test's temporary mocks and saved queues; no assertions were weakened. Unintended changes to `posts.json` and the unrelated runtime-repair test were restored.

## Installation and first checks

Build command from a clean source commit:

```powershell
.\build_release.ps1 -Version 1.1.9 -PreviewRevision content-studio1 `
  -ToolSource 'E:\OPENCLAW\BOB\Highlight destop test\bin' `
  -IconSource 'E:\OPENCLAW\BOB\Highlight destop test\app.ico' `
  -WhisperModelSource 'E:\OPENCLAW\BOB\Highlight destop test\models\faster-whisper-small'
```

Use the installer to update the existing installation. It backs up and preserves mutable ledgers, credentials, config, outputs and `data/`. Do not copy the empty release seed over a populated `posts.json`. The live installed app is left available for the user to update through the installer.

1. Website connection → **Kiểm tra đường video**: CMS mode should explain original YouTube embedding. MP4-only sources need configured SCP.
2. Content Studio: enter a title/niche, choose a profile and rotation mode, enqueue a clip or folder, then watch its filename and stage. Start with 2 concurrent videos; increase to 4 after checking provider capacity.
3. Post Management: expand the token table and filter a Token ID to compare original posts with current Page and group configuration.

## Code and evidence map

- `src/content_packages.py`: generation, queue claims, post reuse, worker settings/lease/stages.
- `src/article_format.py`: normalization, word counts and long source-based fallback.
- `src/first_comment_profiles.py`: custom niches and persistent template rotation.
- `src/publisher/website_publisher.py`: image normalization/cache, shared package rendering and CMS verification.
- `web/token_audit.py`: display-only original-token accounting.
- `web/app.py`: Website diagnostic, Content Studio and token audit endpoints.
- `web/templates/index.html`, `web/index.html`: mirrored UI.
- `tests/test_content_studio_pipeline.py`: rotation, concurrency fencing, shared CMS package, quick generation, square image normalization and token counts.
- Local support: `E:/OPENCLAW/BOB/support/content-studio1/`; its `tools/` contains live/image probes, isolated UI smoke and installer payload verification. Evidence has no raw provider credentials.

Previous checkpoint: `checkpoints/2026-10-04-dashboard-insights1.md`. Use a new revision for any later changes. GitHub publication status and download links are recorded below.


## Final local installer verification

- Packaged code commit: `08727b4d8d1b93f7177b04c277e8010a32f4c7d8`, `source_dirty=false`.
- Installer: `release/Highlight_Desktop_Test_Setup_v1.1.9-content-studio1.exe`.
- Size: **680743936 bytes**.
- SHA-256: **77e9e57aab3548ea451df1f47fcd02b019303fb6d7b4168b161921a3ee178bbd**; the adjacent `.sha256` file matches.
- Payload: **4431 entries**. The verifier checked 18 packaged source files against the checkout, including both identical HTML mirrors, Content Studio, article formatting, Website publishing, token audit and server entrypoint. Post seed is empty; runtime state and credential values are absent.
- Full test suite and all release gate groups completed before the final clean-commit packaging. The final packaging used `-SkipTests` to avoid repeating these completed checks; it retained the packaging guards and all payload verification.
- A standalone copy of this checkpoint is saved as `release/CODEX_CHECKPOINT_v1.1.9-content-studio1.md`.
- Installer is ready locally. The running user installation has not been replaced, and this revision has not been published to GitHub.

Recheck payload with `support/content-studio1/tools/verify_release.ps1 -ExpectedCommit 08727b4d8d1b93f7177b04c277e8010a32f4c7d8` from the workspace root. After this documentation-only commit, the release identity intentionally remains the packaged code commit above.


## Follow-up audit after user screenshot

The screenshot was taken from the still-running prior installation at `http://127.0.0.1:60123` (`E:\OPENCLAW\BOB\Highlight destop test\runtime\python.exe`). A read-only POST to that old process still returned the old `CMS image endpoint does not support video upload` message, and its HTML still showed `Kiểm tra upload video` / `Xử lý 1 mục ngay`. This is evidence of an un-updated runtime, not the new source or installer. The new installer must be applied before testing the updated UI.

The clean source route was exercised with the real CMS configuration and read-only CMS access: HTTP 200, `success=true`, `method=youtube_embed`, `status=embed_ready`, `authenticated=true`, `video_upload_supported=false`. The updated UI says **Kiểm tra đường video**, explains YouTube embedding versus SCP, and names the queue action **Khởi động hàng đợi**. It never calls the CMS image-only MP4 uploader in CMS mode.

The new `support/content-studio1/tools/completion_audit.py` assembled one article using the configured providers and captured all publication arguments without posting a CMS article. It verified text model `ag/gemini-3.6-flash-high` and image model `ag/gemini-3.1-flash-image` were both called once, with 12.28 seconds of overlap. The resulting package contained 862 words, 41 one-sentence paragraphs, three images, a model-generated hero used as `image_url`, two original-video frames, and the original YouTube iframe after the article body. CMS public article verifiers passed against the captured HTML. Forced text-provider failure produced an 829-word title-based fallback with the title, three images, iframe and full-video CTA.

A fresh read-only provider probe then returned a valid normalized image-model thumbnail and a 903-word LLM article in 30.72 seconds; CMS connection remained successful. It made zero Meta writes and published zero test CMS articles. The UI smoke now additionally clicks **Khởi động hàng đợi** and verifies the non-blocking feedback, then submits a batch while preserving the selected First Comment profile, niche and rotation strategy.

## GitHub release and next-session entrypoint

The user has authorized publication of revision `v1.1.9-content-studio1` so they can download and test it. Publication is in progress; the final verification section will record the release ID, uploaded asset digests and public download results. The installer already passed payload verification and retains packaged commit `08727b4d8d1b93f7177b04c277e8010a32f4c7d8`. The release tag will identify that exact commit; later branch commits contain documentation and verification evidence only.

- Release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.1.9-content-studio1
- Installer: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.1.9-content-studio1/Highlight_Desktop_Test_Setup_v1.1.9-content-studio1.exe
- SHA-256 file: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.1.9-content-studio1/Highlight_Desktop_Test_Setup_v1.1.9-content-studio1.sha256
- Standalone checkpoint: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.1.9-content-studio1/CODEX_CHECKPOINT_v1.1.9-content-studio1.md
- Latest checkpoint: https://github.com/minhpark89/Highlight_Video_Studio/blob/release/v1.1.9/CODEX_CHECKPOINT_LATEST.md
- Source branch: `release/v1.1.9`; start a follow-up session by reading this checkpoint and asking for the user's test result on this installed revision.

Do not overwrite this release or move its tag for a future fix. Preserve configuration, tokens, Page bindings, posts, downloads, outputs and `data/`. Read `build_identity.json` from the active installation before investigating; the visible `1.1.9` header alone cannot identify a revision. The prior live installation was left running at port 60123 during publication, and no production CMS article or Meta post was created by these release checks.

Useful targeted checks: `python -m pytest tests/test_content_studio_pipeline.py tests/test_website_ui_regression.py tests/test_text_auth_package_reuse.py tests/test_youtube_embed_publish.py -q --no-header`; full suite: `python -m pytest -q --no-header`. Always keep the two HTML mirrors byte-identical. A Content Studio item that says `website_status=failed` needs its source video/configuration/CMS failure inspected before retrying; preserve the existing stable slug and any article URL rather than inventing a new one.

For token-count reports, compare the original Token ID in `posts.json` with current `pages.json` and group-specific `page_token_bindings`. Keep Pages-with-posts and configured Pages separate, and do not reassign credentials as a display fix. Provider/image failures are independently diagnosed: verify the configured text model and image model, inspect sanitized HTTP status/fallback metadata, then test an isolated package before changing production state.
