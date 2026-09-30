# Checkpoint / session reset — Preview 21 and pending render error (2026-09-30 15:10 GMT+7)

## Source of truth
- Repository: `minhpark89/Highlight_Video_Studio`; local checkout: `F:\openclaw\workspace\highlight-studio-test15-fix`.
- Working branch: `fix/v1.0.19-content-studio-font-image`.
- Published installer: `v1.0.19-desktop-test.21`, tagged source commit `2e3390192a74941de3f53016d1f777550093526d`.
- Current branch before this checkpoint: `af890aef04fbd97e2155419bb540c793e6eb8f6c`; it contains only the render-error diagnosis after the tagged source. This new documentation commit will advance the branch, **not** the preview.21 tag or installer.
- Release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.0.19-desktop-test.21
- Installer: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.0.19-desktop-test.21/Highlight_Desktop_Test_Setup_v1.0.19-preview.21.exe
- Checksum file: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.0.19-desktop-test.21/Highlight_Desktop_Test_Setup_v1.0.19-preview.21.sha256
- Installer SHA-256: `ba13e6c1e3c17597d37a2565b183ec7a24a38f2d27a4a684eff32f7ef97a84ce` (680,588,800 bytes; GitHub release asset state `uploaded`, digest agrees).

## What Preview 21 contains (released)
- Conditional mojibake repair on `/api/jobs`, `/api/jobs/<id>`, `/api/clips`; fixes displayed Vietnamese clip/job metadata without rewriting stored runtime data. Escapes job/clip metadata in the UI.
- Queue render concurrency UI/API: Auto retains existing hardware-profile recommendation, manual bounded at 1–4 simultaneous jobs, limit changes apply to future leases without interrupting active jobs. yt-dlp fragment count per download is unchanged (8).
- Source/tests in commit `2e33901`: `core/text_encoding.py`, `multi_pc/concurrency.py`, `web/app.py`, `src/pipeline.py`, both mirrored HTML templates, and focused tests.
- Last verified: 71 focused/regression tests; release groups 42 + 25 + 44 + 31; packaging guard passed. Source branch and release assets pushed. No 500-video real render/cookie stress test has been verified.
- App-owned Chrome: one UI login entry; code scans cookies under `Default` and `Profile 1`–`Profile 3` when present. This is not a verified multi-account manager or proof that 500 downloads bypass bot checks.

## Known pending render error — do not silently mark fixed
- User screenshot: job `job_1790` (timestamp 2026-09-30 13:05:54), step 3/5, 0/3 clips; Python `charmap` cannot encode U+1EE9 (Vietnamese `ứ`). This job predates Preview 21 release; verify installed build identity before attributing it to Preview 21.
- Step 3 is LLM highlight analysis; step 4 render was not reached. This is an encoding exception, not visual font/CSS or proven YouTube-cookie/concurrency failure.
- Full traceback unavailable; likely candidates include a Vietnamese `print` in LLM exception handling under a legacy Windows stdout encoding or another LLM I/O path. **Root cause unconfirmed**.
- Detailed evidence and next investigation: [CHECKPOINT_RENDER_CHARMAP_20260930.md](CHECKPOINT_RENDER_CHARMAP_20260930.md), commit `af890ae`. Obtain installed build identity + targeted, redacted server log/error; reproduce offline with mock LLM and legacy stdout before patching. Do not rerun real user jobs just to diagnose.

## New session instructions and boundaries
1. Read this checkpoint and `CHECKPOINT_RENDER_CHARMAP_20260930.md`, then verify `git status`, branch HEAD, tag target, and installed build identity before any change. No old chat supersedes current task/user instructions.
2. User intends to reset session and send additional optimization/bug tasks. **Wait for the new task**; do not proactively fix `charmap`, restart app, requeue the 500 jobs, modify YouTube login/profile, call CMS/social, publish, or build another installer until asked.
3. Preserve untracked runtime state `data/content_packages.json`, `data/run/`, `run/` and user installation/profile/cookies. Check working tree separately from the published tag. Do not overwrite or repoint preview.21.
4. If a later fix warrants release, create a new source commit and new preview tag (preview.22 or later, after checking availability); run focused + release tests, verify embedded payload against commit and GitHub asset digest before claiming deployment.
5. No additional issues are specified yet; collect the user's next task after reset rather than inventing them.
