# Checkpoint — preview.17 test handoff

<!-- project: path:F:\openclaw\.openclaw\workspace -->

**Created:** 2026-09-30 (Asia/Bangkok)
**Repository:** `https://github.com/minhpark89/Highlight_Video_Studio`
**Worktree:** `F:\openclaw\workspace\highlight-studio-test15-fix`
**Branch:** `fix/v1.0.19-content-studio-font-image`
**HEAD:** `60e657f0cd818d9523bce4173465c2d60c6eb84a`
**Release:** `v1.0.19-desktop-test.17`

## What is included

- Content Studio retry/font/image fallback fixes from the previous checkpoint.
- UTF-8 subprocess output handling for subtitle rendering.
- Hardware-agnostic Whisper fallback: CUDA failure/unavailability falls back to CPU `int8`.
- Hardware encoder selection: verified NVENC/QSV/AMF, otherwise `libx264`.
- Bounded render concurrency (maximum 4) and adaptive profile defaults.
- Queue deadlock fix: no sleeping while holding `QUEUE_LOCK`.
- Job heartbeat/lifecycle fields and startup recovery of abandoned `running` jobs.
- FFmpeg/yt-dlp timeouts and output integrity checks.
- YouTube cookie fix: yt-dlp now receives the actual app-owned Chrome profile (`Default`/`Profile N`) containing the cookie database, instead of the Chrome user-data root.
- Cookie profile regression tests in `tests/test_youtube_cookie_profile.py`.

## Verification completed

Release gate passed:

- `42` tests
- `25` tests
- `44` tests
- `27` tests
- Total: `138` tests passed
- `python -m py_compile src/pipeline.py` passed.
- Packaging guard passed: no runtime state or machine identity in staged payload.
- Branch pushed to GitHub and release tag resolves to HEAD.
- GitHub release assets uploaded and direct installer URL returned HTTP 200.

Installer:

- URL: `https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.0.19-desktop-test.17/Highlight_Desktop_Test_Setup_v1.0.19-preview.17.exe`
- SHA-256: `7771aaf312c0cc0c4953077e27d635e86ea0af4e8b1ffa3396f8a26cffc42153`
- Size: `680581632` bytes
- Checksum file: `https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.0.19-desktop-test.17/Highlight_Desktop_Test_Setup_v1.0.19-preview.17.sha256`
- Release page: `https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.0.19-desktop-test.17`

## Testing instructions for next session/operator

1. Install preview.17 on the target PC; it is an isolated test product and must not replace the production install.
2. Open YouTube through the app's YouTube/Chrome action so the app-owned `chrome_profile` is used.
3. Log in in that Chrome window, then retry a YouTube download.
4. Test one normal render first, then test a small batch (2–4 videos), then increase batch size.
5. If a failure occurs, capture the exact job error/status, `data` job record, and the app log; do not delete evidence before recording it.
6. For bot-check errors, verify which profile has `Network\Cookies` and whether yt-dlp reports cookie extraction/decryption failure. The app's login status count alone is not proof that yt-dlp successfully decrypted the cookies.
7. For render failures, record selected encoder, Whisper device/compute type, job `attempt`, `heartbeat_at`, `updated_at`, and `error` fields.

## Known limitations / not yet proven

- No real 500-video stress test has been completed.
- No end-to-end YouTube download was run with the boss's authenticated target profile in this environment.
- Chrome cookie decryption may still fail if the target PC's Chrome database is locked, the profile is not the app-owned profile, or Windows DPAPI identity differs; the next session must use the actual target-PC error to continue.
- Full repository `pytest -q` is not a valid release gate because unrelated manual/live tests require external paths and credentials.
- The release is a test release only; do not call it production-ready based solely on the automated gate.

## Safe continuation rule

Start from commit `60e657f` / tag `v1.0.19-desktop-test.17`. Do not rebuild from `.16` or older commits. If a new issue is found, create a new focused fix commit and a new checkpoint before building the next release. Keep `data/run/`, `run/`, test `posts.json`, and generated user state out of commits.
