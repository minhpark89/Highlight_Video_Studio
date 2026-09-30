# Render `charmap` checkpoint — 2026-09-30 15:03 GMT+7

## Scope and release boundary
- Canonical repo: `F:\openclaw\workspace\highlight-studio-test15-fix`, branch `fix/v1.0.19-content-studio-font-image`.
- Released preview.21 source commit: `2e3390192a74941de3f53016d1f777550093526d` (tag `v1.0.19-desktop-test.21`). Do not move or overwrite the tag/release asset.
- This checkpoint is **diagnosis only**. User explicitly requested no render fix/deploy yet while downloading preview.21. No job rerun, YouTube/CMS call, runtime-state edit, installer build, or process restart was performed for this report.
- Preserve untracked `data/content_packages.json`, `data/run/`, and `run/`.

## Observed evidence
- User screenshot: job `job_1790`, timestamp `2026-09-30 13:05:54`, source title `Cop's Gut Feeling Turns Into Missing Teen's Rescue`; status **Lỗi**, step **3/5**, **0/3** clips.
- Both progress and error show truncated `‘charmap’ codec can't encode character '\u1ee9' in position 83: character maps to ...`. U+1EE9 is Vietnamese **ứ**. Screenshot truncates the rest; the complete traceback/encoding is unavailable.
- `web/app.py:344-345` marks step 3 before calling `ask_llm_for_highlights`; step 4 starts only after that call returns. Outer exception handler at `web/app.py:393-401` stores the exception text in `progress_msg`/`error`; therefore the persisted `charmap` string describes a Python UnicodeEncodeError that escaped from step 3, not a CSS/font rendering issue. Step 4 FFmpeg has not been reached for this attempt.
- `src/pipeline.py:618-715` builds a Vietnamese prompt from transcript, POSTs to the LLM, and on any exception prints `[LLM Error] Không trích xuất được highlight từ LLM: {e}` before returning a fallback. On Windows, the hidden desktop launcher (`AppLauncher.cs`, `StartServer`) redirects Python stdout/stderr and appends received lines to `server_error.log`; no explicit UTF-8 stdout encoding is configured in the launcher or `run_server.py`. A non-UTF-8 console pipe can fail to encode a Vietnamese `print`, including U+1EE9 in the LLM error, masking the original exception. **This is a plausible source, not confirmed root cause** without full traceback and active process encoding.
- Other step-3 risk: the LLM client or a downstream I/O path could raise UnicodeEncodeError before its fallback. Current evidence does not isolate which call or the underlying LLM error. Read-only source inspection confirmed job JSON writes use explicit UTF-8 in `web/app.py:245-260`; this alone does not implicate persisted storage.

## Next investigation (after user authorizes a later fix)
1. Record the installed build identity and full `error`/`progress_msg` for `job_1790` from the *user's installed instance*, without overwriting job files. Retrieve only the relevant timestamped lines from `server_error.log`; redact credentials and personal data. Do not assume the local repository's runtime folder is the user's installed instance.
2. Reproduce offline with a fake LLM failure and Vietnamese transcript under Windows `cp1252`-encoded redirected stdout; capture traceback and `sys.stdout.encoding`/`sys.stderr.encoding`. Mock network and leave all real queue entries untouched.
3. If the print path is confirmed, make failure logging encoding-safe and preserve the original LLM exception; test both UTF-8 and legacy code-page stdout and verify deterministic fallback. If not confirmed, trace the exact stack in LLM request/response handling before editing.
4. Run focused render/LLM tests, full release tests, package identity/payload checks; only then make a **new** preview tag (never replace preview.21) when explicitly requested.

## Open questions
- Did the error originate in `print` after an LLM error or during the LLM call itself? Requires traceback.
- Is `job_1790` from preview.20 or preview.21? Screenshot timestamp predates preview.21 publication; likely older build, but verify installed identity rather than assume.
- No proof yet that YouTube cookies or chosen concurrency caused this failure; the displayed failure is at the LLM stage.
