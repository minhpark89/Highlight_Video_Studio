# Highlight Video Studio hotfix checkpoint — preview.13

Saved: 2026-09-29 (Asia/Bangkok, GMT+7)

## Source

- Canonical worktree: `F:\openclaw\.openclaw\workspace\worktrees\highlight-multi-pc`
- Branch: `feature/multi-pc-control-plane`
- Hotfix commit: `6519f4585a382bbd46048e729ccac3c5b96eb7c8`
- Remote branch verified at the same commit.
- Hotfix scope: defensive 9router/OpenAI-compatible JSON/SSE/markdown response parsing and numeric/string Page ID normalization before publish preflight.
- Runtime/generated files intentionally excluded from commit: `posts.json`, `data/content_packages.json`, `data/run/`, `run/`.

## Production deployment

- Production root: `D:\Highlight_Video_Studio`
- Listener: `127.0.0.1:5080`
- Production PID after final deployment restart: `16772`
- Command: `pythonw.exe web\app.py`
- Root health check: HTTP `200`, response size `358031` bytes.
- Live `/api/llm/test`: HTTP `200`, `success=true`.
- Live `/api/image-provider/test`: HTTP `200`, `success=true`.

### Source/production SHA256 matches

- `src/content_builder.py`: `0bbbfde4b0f441387655b143cd404a0a68124af63a439ba823871f977335c546`
- `src/content_packages.py`: `8a0920e7728ffd1fc9d5756a87694bd4b886937466ab3d9a6945607d8360b25c`
- `src/pipeline.py`: `10747a6037d3ac2b8a83b98394bc20143d6db7f1edad18083cee4fa221a8d7ae`
- `src/publisher/website_publisher.py`: `3b4156beb744f7323f7d51f5d3e10bbe6abe1be5144611d30c0f30615630865c`
- `web/app.py`: `ef9dceca030e224eb6cdaeee8436f1b66e298bc784d4d323cef52438c31a5320`
- `src/llm_response.py`: `27fa37380bb4ba28cb4d60571d6b57718342999b01ed27b61fd0148c32c9a0ee`

## Verification

- Changed Python modules compiled successfully.
- Parser canaries passed for conventional JSON, SSE chunks, markdown-fenced JSON, and prose-wrapped JSON.
- Targeted hotfix/release suite: `112 passed`.
- Installer build release gates: `42 passed`, `25 passed`, `42 passed`, `3 passed`.
- Packaging guard: clean; no runtime state or machine identity included.

## Installer and release

- Version: `v1.0.19-preview.13`
- Tag: `v1.0.19-desktop-test.13`
- Installer: `release\Highlight_Desktop_Test_Setup_v1.0.19-preview.13.exe`
- Size: `683574272` bytes
- Installer SHA256: `5d8be8b562ae09c48dd0c3cb1a6892179a6636fcc09179c3e7cc4b6b2d52584b`
- Local `.sha256` file matches the installer.
- GitHub release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.0.19-desktop-test.13
- Installer download: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.0.19-desktop-test.13/Highlight_Desktop_Test_Setup_v1.0.19-preview.13.exe
- Remote asset verified HTTP `200`, `Content-Length: 683574272`, GitHub digest matches the local installer SHA256.

## Preserved production state

Deployment changed only the six hotfix source files listed above. The following persistent state was preserved and not copied, replaced, deleted, or packaged:

- `tokens_vault.json`
- `pages.json`
- `page_groups.json`
- `posts.json`
- `jobs.json`
- `downloads/`
- `output/`
- `chrome_profile/`

## Restart/resume instructions

1. Gateway restart is safe; source, production deployment, release, and this checkpoint are durable.
2. Verify production before taking action:
   - Confirm a listener on port `5080`.
   - Request `http://127.0.0.1:5080/` and require HTTP `200`.
3. If port `5080` is not listening, start only the Highlight Video Studio process from `D:\Highlight_Video_Studio` using its existing launcher (`Start_Studio.bat`) or run `pythonw.exe web\app.py` with that directory as the working directory. Do not stop unrelated Chrome processes and do not replace persistent JSON/state directories.
4. Resume source work from branch `feature/multi-pc-control-plane`; verify the remote contains hotfix commit `6519f4585a382bbd46048e729ccac3c5b96eb7c8`.
5. Do not commit the runtime/generated files listed in the Source section.
