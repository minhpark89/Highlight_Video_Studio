# Highlight Video Studio local-first desktop — Phase 1 checkpoint and handoff

- **Date:** 2026-09-28 (Asia/Bangkok)
- **Branch/worktree:** `feature/multi-pc-control-plane` in `F:\openclaw\.openclaw\workspace\worktrees\highlight-multi-pc`
- **Deployment state:** source-only; not deployed, not installed
- **Spec version:** `2026-09-28.phase1-v2-local-desktop` (supersedes the cloud-first `2026-09-28.phase1` draft)

## What changed since the first checkpoint

The product direction moved from "cloud control plane with a PC connector" to a **local-first installed desktop application**. The cloud is now deliberately optional and small.

- Desktop app per PC owns UI, backend, pipeline, secrets, browser profiles, media, and rendering. No inbound port, no router change, no reverse tunnel, no published 5080.
- Cloud scope reduced to login/licence activation, update checks, and optional lightweight metadata sync. Cloud is never required for rendering.
- Added `multi_pc/hardware.py`: hardware inspection (GPU/CPU/RAM/disk), FFmpeg encoder enumeration, a short disk write probe, per-encoder canary encodes, and `derive_render_profile()` with safe concurrency/RAM bounds.
- Added `multi_pc/profile_cache.py`: profile cached with a hardware/driver fingerprint and TTL; invalidated on driver/hardware change or OS platform change; forced re-probe supported.
- Updated `multi_pc/connector.py` and `multi_pc/__init__.py` so local rendering and job handling work independently when the cloud is unreachable.
- Updated `multi_pc/README.md` with hardware/cache commands, in-process/loopback backend binding, and the outbound-only connector.
- Rewrote `docs/multi-pc-phase1-architecture-v1.md` for the local-first model: desktop shell, cloud scope, offline behavior, benchmark/profile policy, installer/startup/update lifecycle, and migration from the port-5080 browser app.

## Completed

- Audited the 55-route Flask application and classified cloud metadata versus PC-only data/actions (`docs/multi-pc-phase1-architecture-v1.md` §2).
- Architecture, threat model, cloud API contract, executable SQLite schema, job state machine, reconnect/idempotency rules, resource expectations, and cutover/rollback plan — all rewritten for local-first.
- Standalone cloud control plane with health, registration disabled by default, password/session scaffolding, one-time device pairing, heartbeat, account-owned job creation/read, and device-only lease/progress/complete.
- Outbound HTTPS connector and safe local adapter dispatching only allowlisted Python callables. No generic command, shell, `eval`, or inbound local server.
- Protected credential-store interface: plaintext save refused; production Windows work must implement DPAPI/Credential Manager.
- Hardware benchmark with NVENC → QSV → AMF → CPU fallback and cached, fingerprint-validated render profile.
- Installer/startup/update and migration design documented, including per-user install, signed updates, loopback-only transitional backend, and copy-not-move data migration.

## Changed files

- `multi_pc/__init__.py`
- `multi_pc/adapter.py`
- `multi_pc/connector.py`
- `multi_pc/connector_main.py`
- `multi_pc/control_plane.py`
- `multi_pc/credentials.py`
- `multi_pc/hardware.py` (new)
- `multi_pc/profile_cache.py` (new)
- `multi_pc/schema.sql`
- `multi_pc/security.py`
- `multi_pc/README.md`
- `tests/test_multi_pc_phase1.py`
- `tests/test_multi_pc_hardware.py` (new)
- `docs/multi-pc-phase1-architecture-v1.md`
- `docs/multi-pc-phase1-checkpoint-2026-09-28.md`

## Verification commands

```powershell
python -m pytest tests\test_multi_pc_phase1.py tests\test_multi_pc_hardware.py -q
Get-ChildItem multi_pc\*.py | ForEach-Object { python -m py_compile $_.FullName }
git diff --check
Select-String -Path web\app.py -Pattern '^APP_VERSION'
git diff -- web\app.py run_server.py
```

Expected targeted result: `12 passed`. `APP_VERSION` remains `1.0.19`; no diff exists for `web/app.py` or `run_server.py`.

## Runnable state

- `python -m multi_pc.control_plane` starts the development control plane on PC loopback `127.0.0.1:5090`; it does not expose port 5080.
- `python -m multi_pc.connector_main` is an outbound connector scaffold requiring a control-plane URL and protected device credential from its supervisor/store. It registers no production local handlers and therefore fails closed until canary integration.
- Hardware probe and profile cache are usable without any cloud component: `inspect_hardware()`, `derive_render_profile()`, `ProfileCache()`.
- SQLite initializes from `multi_pc/schema.sql`. Production should migrate the constraints to PostgreSQL before multi-instance scaling.

## Production boundaries verified

- No active-runtime file under `D:\Highlight_Video_Studio` was read for modification or changed.
- No VPS, DNS, Caddy, Basic Auth, scheduler, router, or tunnel setting was changed.
- No credential or object-storage requirement was added.
- No application version or release tag was changed.
- The existing v1.0.19 app and reverse-tunnel trial remain separate from this skeleton.

## Phase 2 / canary handoff

1. Build the desktop shell (WebView/native) with single-instance guard, in-process or per-run-token loopback backend binding, and installer signing.
2. Implement a DPAPI/Credential Manager device and provider-secret store with per-user ACLs, plus credential revoke/rotation.
3. Add a durable local execution-receipt ledger keyed by job/action id before wiring non-idempotent publication.
4. Register narrow local handlers around existing download/transcript/render and Zernio paths; validate URLs and resolve all secrets locally. Keep publish approval gates local.
5. Add cloud licence/entitlement and update-manifest endpoints; signed, user-confirmed, rollback-capable updates.
6. Add secure-cookie browser sessions, CSRF, login throttling, account lifecycle, audit logs, retention, PostgreSQL migrations, monitoring, and proxy body/rate limits on the cloud side.
7. Run a one-PC canary with the tunnel still available for rollback; remove Basic Auth and disable the reverse tunnel only in a coordinated cutover after auth and isolation review pass.
8. Optionally add direct signed object-storage uploads with bounded object key, method, size, expiry, checksum, and no VPS media proxy.
9. Expand hardware coverage: additional AMD/Intel detection paths, multi-GPU policy, thermal/power throttling awareness.

## Expected resource profile

- Cloud: metadata JSON and DB operations only; no downloads, Whisper, FFmpeg, GPU, browser automation, or media storage.
- Local backend idle: dominated by the existing runtime; one active job per device by default, raised only when the benchmark allows.
- Hardware probe: a few seconds of tooling calls plus one short canary per candidate encoder; cached for 7 days and re-run on fingerprint change.
- Disk: benchmark/canary need room for a ~64 MB temporary probe and short canary outputs, both cleaned up.
- Media paths remain source → PC and, if later enabled, PC → object storage directly.
