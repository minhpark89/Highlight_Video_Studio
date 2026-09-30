# Checkpoint / Handoff — Preview 20 (2026-09-30 12:35 GMT+7)

## Canonical repository state
- Repository: `minhpark89/Highlight_Video_Studio`
- Local path: `F:\openclaw\workspace\highlight-studio-test15-fix`
- Branch: `fix/v1.0.19-content-studio-font-image`
- Preview source commit: `d00b2d6f8fa840a210b02c69cb8042d4b8415ba6` — `fix: harden content studio article and retry flow`
- Preview tag: `v1.0.19-desktop-test.20`
- GitHub release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.0.19-desktop-test.20

## Preview 20 changes
- Content Studio now matches clip metadata by normalized path and basename, preventing a stale/old article URL caused by path-form differences.
- CMS article creation is performed for the current clip when website generation is enabled.
- A First Comment is blocked unless a newly published CMS article has a verified public URL and the rendered public article contains the original video embed.
- Added rendered-page embed verification for YouTube `youtube-nocookie.com/embed/<id>` and public MP4 stream markers.
- First Comment must contain the exact verified CMS article URL.
- Content Studio retry buttons show immediate busy state, spinner, disabled state, `aria-busy`, and clear success/error feedback.
- Repaired Content Studio Vietnamese text/font encoding and kept `web/index.html` synchronized with `web/templates/index.html`.
- Added regression coverage for missing/exact embed markers and publisher verification calls.

## Verification evidence
- Focused tests: **63 passed**.
- Release test groups: **42 + 25 + 44 + 31 passed**.
- Both HTML template scripts parse successfully with Node.
- Python compilation and `git diff --check` passed.
- Packaging guard passed.
- Installer embedded identity verified:
  - source commit `d00b2d6f8fa840a210b02c69cb8042d4b8415ba6`
  - prerelease `1.0.19-preview.20`
  - build channel `desktop-test`
  - bind host `127.0.0.1`
- Embedded source files match committed source after LF/CRLF normalization.
- Branch and tag were pushed; tag resolves to the preview source commit.

## Published assets
- Installer: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.0.19-desktop-test.20/Highlight_Desktop_Test_Setup_v1.0.19-preview.20.exe
- Checksum: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.0.19-desktop-test.20/Highlight_Desktop_Test_Setup_v1.0.19-preview.20.sha256
- Installer size: **680,585,216 bytes**
- Installer SHA-256: `2a341543a89b0f7fb6fc865ae41d076bd843fd3f43ed8b72147ebd60266d5387`
- GitHub reports both named assets as `uploaded`; installer digest matches local SHA-256.
- Exact installer download endpoint HEAD returned HTTP 200 with `Content-Length: 680585216`.

## Continuation instructions
1. Do not overwrite or repoint preview.20. Any next fix must use preview.21.
2. Start by reading this handoff and checking `git status`.
3. Preserve untracked runtime data (`data/content_packages.json`, `data/run/`, `run/`) unless specifically asked to clean it; these are not release source.
4. Do not call a live CMS or social platform during tests. Mock CMS responses and verify the public-article/embed gate in regression tests.
5. If First Comment is missing, stale, or has a URL not present in the verified article, keep the item failed/retryable and do not publish the comment.
6. Desktop-test remains side-by-side, loopback-only, with separate product/shortcut identity and scoped process handling.

## Known environment notes
- Agent preflight reported API endpoint `401 Unauthorized` and no ADB device; these did not block local code tests or GitHub release publication.
- GitHub release was published using authenticated account `minhpark89`.
