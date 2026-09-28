# Highlight Video Studio — desktop preview install, startup, update and migration

- **Build:** `1.0.19-preview.1` (`highlight-desktop-offline-preview`)
- **Scope:** local-first offline preview; no cloud, no tunnel, no public port
- **Production untouched:** `D:\Highlight_Video_Studio`, `APP_VERSION = "1.0.19"`, port 5080 and the existing supervisor all keep running unchanged

## Why the build name differs from `APP_VERSION`

`APP_VERSION = "1.0.19"` in `web/app.py` is the **production release identity** shown in the UI and used for release tags. The preview keeps it frozen so production semantics are preserved, and carries a separate build identity instead:

| Field | Value | Meaning |
|---|---|---|
| `APP_VERSION` | `1.0.19` | production release; never changed by preview work |
| `PRERELEASE_NAME` | `highlight-desktop-offline-preview` | preview product/channel name |
| `PRERELEASE_BUILD` | `1.0.19-preview.1` | preview build string; distinct from the release tag |

Both values come from `multi_pc/environment.py`, so the preview identity can never be confused with a production release.

## Install

Non-destructive, side-by-side, fail-closed:

```powershell
python install_preview.py --build --json                              # create the payload zip
python install_preview.py --payload <zip> --json                      # install side-by-side
python install_preview.py --payload <zip> --target D:\Highlight_Video_Studio   # refused: exit 1
```

- Default target: `%LOCALAPPDATA%\Programs\highlight-desktop-offline-preview`.
- The installer **refuses** a target equal to or inside `D:\Highlight_Video_Studio` (`production_safety()`), and refuses zip members that would escape the target directory.
- Zip members are extracted only after the path check; an uninstall manifest (`preview_install_manifest.json`) records build, install root, payload SHA256, bind policy and the uninstall note.
- Existing data is **read, never overwritten**: the preview keeps its own `data/` directory and never writes into the production data folders.
- The installer deliberately does not stop, signal, restart, or inspect production processes.

## Startup

```powershell
python run_local.py          # from the install root or the repo
Launch_Highlight_Desktop_Preview.cmd   # installed convenience wrapper
```

1. A free ephemeral loopback port is requested from the OS (`pick_free_port`); port 5080 is explicitly refused because it belongs to production.
2. A fresh per-run session token is generated (`secrets.token_urlsafe`).
3. The existing Flask app is imported and wrapped in the session guard.
4. The port + token are written to `%LOCALAPPDATA%\HighlightVideoStudio\run\runtime.json` (0600 where supported) so the shell/desktop can attach; the file is removed on shutdown.
5. Waitress serves on `127.0.0.1` only.

**Request gating:** every request must come from a loopback client and carry `X-Highlight-Session: <token>` (or the `highlight_session` cookie). Missing/incorrect token → `401`. Non-loopback client → `401` even with a valid token. `/healthz` is exempt for readiness probes. There is no Basic Auth and nothing is published.

## Update

- The preview is update-free by design: it is a side-by-side artifact, so replacing it is "install a new side-by-side directory", never an in-place upgrade of production.
- A future signed update can reuse the same payload/`install_preview.py` shape with a version manifest and hash verification; the preview never rewrites files under the production root.
- Rollback is deleting the preview install root; production is intact because it was never modified.

## Migration from the port-5080 browser app

1. Leave production, its supervisor and the reverse tunnel exactly as they are while the preview is evaluated.
2. Start the preview from its own directory; it reads config/ledgers copy-on-read and writes only under its own `data/`.
3. Replace browser Basic Auth with the loopback session token for shell↔backend calls.
4. Once the desktop shell is verified on a canary PC, retire the tunnel and any public publishing of the local app. Never overlap a public unauthenticated window.
5. Migration of live data is a **copy**, not a move; the first launch runs read-only against media and only enables writes after verification.

## Verification commands

```powershell
python -m pytest tests\test_multi_pc_phase1.py tests\test_multi_pc_hardware.py tests\test_multi_pc_local_mvp.py -q
python -m pytest tests\test_release_guards.py tests\test_page_token_sync.py -q
python -m py_compile multi_pc\hardware.py multi_pc\local_launcher.py multi_pc\environment.py install_preview.py run_local.py
python install_preview.py --build --json
Get-FileHash -Algorithm SHA256 release\Highlight_Desktop_Preview_v1.0.19-preview.1.zip
Select-String -Path web\app.py -Pattern '^APP_VERSION'
```

Expected: `35 passed`, `41 passed`, `APP_VERSION = "1.0.19"`, and a payload hash matching the published SHA256 file.
