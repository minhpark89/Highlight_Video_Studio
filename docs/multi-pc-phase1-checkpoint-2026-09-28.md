# Multi-PC Phase 1 → local-first desktop MVP — checkpoint

- **Date:** 2026-09-28 (Asia/Bangkok)
- **Branch:** `feature/multi-pc-control-plane` in `F:\openclaw\.openclaw\workspace\worktrees\highlight-multi-pc`
- **Build:** `1.0.19-preview.1` (`highlight-desktop-offline-preview`)
- **Status:** testable 1-PC MVP complete; production untouched; cloud control plane deferred to Phase 2

## Deliverables

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Hardware probe + real FFmpeg canary + selected profile JSON | done | `multi_pc/hardware.py`, `multi_pc/environment.py`, profile JSON below |
| 2 | Local-only desktop launcher, loopback isolated, no tunnel | done | `multi_pc/local_launcher.py`, `run_local.py` |
| 3 | Offline test installer, clearly marked pre-release version | done | `install_preview.py`, `1.0.19-preview.1` |
| 4 | Install side-by-side, preserve data, don't disturb production | done | manifest + guard test + production 5080 still `200` |
| 5 | Short render canary executed on this PC | done | NVENC 3.64x realtime, ffprobe-validated |
| 6 | Checkpoint, SHA256, exact installer path | done | paths and hashes below |

## 1 + 5. Hardware probe and real render canary (this PC)

Measured on `DESKTOP-COM8UQ7`, build `1.0.19-preview.1`, 2026-09-28T01:11:22Z:

| Fact | Value |
|---|---|
| GPU | NVIDIA GeForce RTX 3060, 12288 MB VRAM, driver 610.88 |
| CPU | Intel Xeon E5-2680 v4 ×2 — 28 physical / 56 logical cores |
| RAM | 98,206 MB |
| Disk | 257,447 MB free, 1,247 MB/s measured write |
| FFmpeg / ffprobe | 8.1.2 essentials (`D:\AI\tools\ffmpeg_new\...\bin`) |

**Encoder canaries** (real 1080p30 encodes, artifact validated with `ffprobe -count_frames`):

| Encoder | Listed by `-encoders` | Canary success | Time (2s clip) | Realtime | Output |
|---|---|---|---|---|---|
| NVENC `h264_nvenc` | yes | **yes** | 0.551 s | **3.63x** | 2,969,394 B, 1920x1080, 60 frames |
| QSV `h264_qsv` | yes | no | 0.065 s | — | failed (no Intel iGPU) |
| AMF `h264_amf` | yes | no | 0.038 s | — | failed (no AMD GPU) |
| CPU `libx264` | yes | yes | 0.386 s | 5.18x | 1,365,515 B, 1920x1080, 60 frames |

QSV and AMF are compiled into this FFmpeg build, so a name-list check would have wrongly selected them. Only the canary encode + ffprobe validation revealed the truth — this is why device names are never trusted.

**Selected profile JSON** (`%LOCALAPPDATA%\HighlightVideoStudio\cache\render_profile.json`):

```json
{
  "profile_version": 2,
  "encoder": "nvenc",
  "codec": "h264_nvenc",
  "encoder_label": "nvidia-nvenc",
  "concurrency": 2,
  "max_concurrent_renders": 2,
  "hardware_decode": true,
  "ram_budget_mb": 58923,
  "canary": {
    "encoder": "nvenc", "elapsed_seconds": 0.55, "realtime_factor": 3.64,
    "output_bytes": 2969394, "width": 1920, "height": 1080, "frames": 60
  },
  "notes": ["Canary verified nvenc at 3.64x realtime (0.55s for 2.0s 1080p30)."]
}
```

Regenerate with `python -m multi_pc.environment` or `run_local.py`. The cache invalidates on driver/GPU/CPU/RAM/OS change, or with a forced re-probe.

## 2. Local-only launcher

`python run_local.py` (or the installed `Launch_Highlight_Desktop_Preview.cmd`):

- Requests an ephemeral free loopback port from the OS; **port 5080 is explicitly refused**.
- Generates a per-run `secrets.token_urlsafe` session token.
- Wraps the existing Flask app in `SessionGuard`: loopback clients only, token required, `/healthz` exempt.
- Writes `%LOCALAPPDATA%\HighlightVideoStudio\run\runtime.json` for shell attachment; deletes it on shutdown.
- No tunnel, no Basic Auth, no public bind, no cloud dependency.

**Live verification:** installed preview on port 61716 → `/api/system/info` returned `401` without the token and `200` with it, while production on 5080 kept answering `200` throughout.

## 3 + 4. Offline installer

| Item | Value |
|---|---|
| Payload | `release\Highlight_Desktop_Preview_v1.0.19-preview.1.zip` |
| Payload SHA256 | `dd5065ef4940241463a7dd3ef2d7a8e2d9ef3f41a9a7f9f366f877fdc9e71d7d` |
| Payload size | 404,076 bytes |
| Installed root | `C:\Users\Admin\AppData\Local\Programs\highlight-desktop-offline-preview` |
| Manifest | `<install root>\preview_install_manifest.json` |
| Launcher | `<install root>\Launch_Highlight_Desktop_Preview.cmd` |

- Pre-release identity is explicit: `PRERELEASE_NAME = highlight-desktop-offline-preview`, `PRERELEASE_BUILD = 1.0.19-preview.1`, while `APP_VERSION` stays `1.0.19` as the production release identity. See `docs/desktop-preview-install-startup-update.md`.
- Installing to `D:\Highlight_Video_Studio` is **refused** (`PreviewInstallError`, exit 1) and zip entries that escape the target are rejected.
- The installer never stops, restarts, or signals any process; production was verified still serving on 5080 after install.

## Changed / added files

- Added: `multi_pc/local_launcher.py`, `multi_pc/environment.py`, `run_local.py`, `install_preview.py`
- Added: `tests/test_multi_pc_local_mvp.py`, `docs/desktop-preview-install-startup-update.md`
- Changed: `multi_pc/hardware.py` (measured `benchmark_encoders`, profile canary evidence, `PROFILE_CACHE_VERSION = 2`)
- Changed: `web/app.py` (`detect_hardware` tolerant of a missing/None cached profile — fixes a latent 500 on a clean install)
- Updated: `multi_pc/README.md`, `docs/multi-pc-phase1-architecture-v1.md`

## One deliberate deviation

The offline preview has no cloud component, so **no `/healthz` route was added to the production app**. Its plan entry is documented in `docs/desktop-preview-install-startup-update.md` and stays deferred to Phase 2 rather than modifying the production app for a preview-only endpoint.

## Test evidence

```powershell
python -m pytest tests\test_multi_pc_phase1.py tests\test_multi_pc_hardware.py tests\test_multi_pc_local_mvp.py -q   # 35 passed
python -m pytest tests\test_release_guards.py tests\test_page_token_sync.py -q                                        # 41 passed
```

The whole-repo `python -m pytest -q` run collects unrelated legacy scratch scripts at the repo root (which exit on `sys.exit`, killing collection) and resolves `core` to the neighbouring `D:\News_Video_Studio` instead of the worktree when cwd differs. Those are pre-existing repo issues: the product guard suites pass when run against the worktree root, which is what these verification commands do.

## Production boundaries verified

- `APP_VERSION` still `1.0.19`; no release tag touched.
- `D:\Highlight_Video_Studio` never written to; production returned `200` before and after the full preview install and run.
- Port 5080 never bound, proxied, or reused; no tunnel, DNS, Caddy, firewall, router, or scheduler change.
- No credentials or secrets in the payload, manifest, logs, or command line.

## Next

1. Desktop shell (WebView/native) with single-instance guard, auto-attaching the runtime token.
2. Production-grade installer (MSI/EXE, code-signed) wrapping the same payload + `install_preview.py` logic, plus `installer/startup/update` lifecycle.
3. DPAPI/Credential Manager secret store and a local execution-receipt ledger keyed by job/action id.
4. Register narrow local handlers (download/transcript/render, Zernio publish) with local approval gates.
5. Only then reintroduce cloud login/licence/update as Phase 2.
