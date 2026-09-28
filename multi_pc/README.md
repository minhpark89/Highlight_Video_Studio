# Highlight Video Studio — local-first multi-PC module

This directory is the local-first desktop/PC runtime plus the optional cloud control plane. It is isolated from the running v1.0.19 Flask install: it does not import or expose `web.app`, and nothing here is deployed.

Read `docs/multi-pc-phase1-architecture-v1.md` for the decision record and `docs/multi-pc-phase1-checkpoint-2026-09-28.md` for delivered MVP evidence. Short version: each PC is an installed desktop app that owns its own UI, backend, secrets, browser profiles, media, and rendering. No inbound port, no reverse tunnel, no published 5080. Cloud is optional and limited to login/licence/update and small job metadata.

## Offline preview quick start

```powershell
python install_preview.py --build --json                  # build the preview payload
python install_preview.py --payload <zip> --json         # install side-by-side (production untouched)
python run_local.py                                      # loopback-only desktop launcher
```

- `run_local.py` binds an OS-assigned ephemeral loopback port (never 5080) and requires the per-run session token from `%LOCALAPPDATA%\HighlightVideoStudio\run\runtime.json` in `X-Highlight-Session`.
- `install_preview.py` refuses any target equal to or inside `D:\Highlight_Video_Studio`, and never stops or signals production processes.
- Build identity: `PRERELEASE_NAME = highlight-desktop-offline-preview`, `PRERELEASE_BUILD = 1.0.19-preview.1`, while `APP_VERSION` stays `1.0.19`.

```powershell
python -c "import json; from multi_pc.environment import environment_report; print(json.dumps(environment_report()['render_profile'], indent=2))"
```

## Hardware detection, benchmark, and profile cache

- `collect_hardware_report()` collects GPU vendor/model/VRAM/driver, CPU cores/model, RAM, free disk, a measured disk write probe, and the FFmpeg encoder list.
- `benchmark_encoders()` runs a real 1080p canary per candidate in order **NVENC → QSV → AMF → CPU** and validates each artifact with `ffprobe`. Listing a codec is never sufficient.
- `derive_render_profile()` returns the selected encoder, hardware-decode flag, max concurrency, RAM budget, canary evidence and notes. CPU fallback and low RAM force concurrency 1; low disk adds a purge warning.
- `ProfileCache` stores the profile with a hardware/driver fingerprint and TTL (default 7 days) and invalidates on driver/hardware/OS change; forced re-probe bypasses the cache.

```powershell
python -c "from multi_pc.profile_cache import ProfileCache; c=ProfileCache(); print(c.get())"
```

- `ProfileCache` stores the derived profile with a hardware/driver fingerprint and TTL (default 7 days).
- The cache is invalidated automatically when the fingerprint changes (driver update, GPU/RAM/CPU swap, OS platform change) and can be bypassed with a forced re-probe.

## Control plane (development only)

```powershell
$env:FLASK_ENV = "production"
python -m multi_pc.control_plane
```

Binds only `127.0.0.1:5090` in development. Production must run a WSGI server behind HTTPS with production session/rate-limit/CSRF controls described in the architecture doc. Self-registration is disabled by default.

## Local backend / desktop shell binding

- Preferred: shell talks to the backend **in-process** or over a per-run loopback channel with a generated local session token. No fixed shared secret, nothing public.
- Transitional Flask: bind **loopback only** on an isolated or random port, never 5080, never published; write the port/token to a per-user ACL-protected runtime file.

## Connector (development/canary scaffold)

Supply the paired device credential through a protected process environment or a future DPAPI store, never a command-line argument or committed file:

```powershell
$env:HIGHLIGHT_CONTROL_PLANE_URL = "https://highlight.shopkitai.com"
python -m multi_pc.connector_main
```

The credential variable is intentionally omitted from the example. `connector_main` registers no production handlers, so leased actions fail closed until an allowlisted local integration is explicitly provided. The connector is outbound HTTPS only and retries with backoff; local jobs and rendering continue while the cloud is unreachable.

## Tests

```powershell
python -m pytest tests\test_multi_pc_phase1.py tests\test_multi_pc_hardware.py tests\test_multi_pc_local_mvp.py -q
```
