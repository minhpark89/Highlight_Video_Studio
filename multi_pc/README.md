# Phase 1 runnable skeleton

This directory is isolated from the v1.0.19 Flask runtime. It does not import or expose `web.app`.

## Control plane (development only)

```powershell
$env:FLASK_ENV = "production"
python -m multi_pc.control_plane
```

The development entry point binds only to `127.0.0.1:5090`. Production deployment must use a WSGI server behind HTTPS and must supply production session/rate-limit/CSRF controls described in `docs/multi-pc-phase1-architecture-v1.md`. Self-registration is disabled by default.

## Connector (development/canary scaffold)

Supply the paired device credential through a protected process environment or future DPAPI store, never a command-line argument or committed file:

```powershell
$env:HIGHLIGHT_CONTROL_PLANE_URL = "https://highlight.shopkitai.com"
python -m multi_pc.connector_main
```

The credential variable is intentionally omitted from the example. `connector_main` registers no production handlers, so leased actions fail closed until an allowlisted local integration is explicitly provided.

## Tests

```powershell
python -m pytest tests\test_multi_pc_phase1.py -q
```
