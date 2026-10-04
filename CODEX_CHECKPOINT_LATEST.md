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

Previous checkpoint: `checkpoints/2026-10-04-dashboard-insights1.md`. Use a new revision for any later changes. This checkpoint describes a local installer delivery; GitHub publication is not recorded as completed.


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
