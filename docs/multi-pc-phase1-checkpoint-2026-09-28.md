# Multi-PC Phase 1 checkpoint and handoff

- **Date:** 2026-09-28 (Asia/Bangkok)
- **Branch/worktree:** `feature/multi-pc-control-plane` in `F:\openclaw\.openclaw\workspace\worktrees\highlight-multi-pc`
- **Deployment state:** source-only; not deployed or installed

## Completed

- Audited the existing 55-route Flask application and classified cloud metadata versus PC-only data/actions.
- Added versioned architecture, threat model, API contract, executable schema, job state machine, reconnect/idempotency rules, resource expectations, and cutover/rollback plan.
- Added a standalone control-plane service with health, disabled-by-default registration, password/session scaffolding, one-time device pairing, heartbeat, account-owned job creation/read, device-only lease/progress/complete, and secret rejection/redaction.
- Added an outbound HTTPS polling connector and a safe local adapter that dispatches only allowlisted Python callables. There is no generic command or inbound local server.
- Added a protected credential-store interface. Plaintext saving is refused; production Windows work must implement DPAPI/Credential Manager.
- Added tests for account/device isolation, expired pairing, create/lease idempotency, reconnect reclaim, safe completion behavior, adapter dispatch, and secret redaction.

## Changed files

- `multi_pc/__init__.py`
- `multi_pc/control_plane.py`
- `multi_pc/schema.sql`
- `multi_pc/security.py`
- `multi_pc/adapter.py`
- `multi_pc/connector.py`
- `multi_pc/connector_main.py`
- `multi_pc/credentials.py`
- `multi_pc/README.md`
- `tests/test_multi_pc_phase1.py`
- `docs/multi-pc-phase1-architecture-v1.md`
- `docs/multi-pc-phase1-checkpoint-2026-09-28.md`

## Verification commands

```powershell
python -m pytest tests\test_multi_pc_phase1.py -q
Get-ChildItem multi_pc\*.py | ForEach-Object { python -m py_compile $_.FullName }
git diff --check
Select-String -Path web\app.py -Pattern '^APP_VERSION'
git diff -- web\app.py run_server.py
```

Expected targeted result: `6 passed`. `APP_VERSION` remains `1.0.19`; no diff exists for `web/app.py` or `run_server.py`.

## Runnable state

- `python -m multi_pc.control_plane` starts the development control plane on PC loopback `127.0.0.1:5090`; it does not expose port 5080.
- `python -m multi_pc.connector_main` is an outbound connector scaffold. It requires a control-plane URL and protected device credential from its supervisor/store. It has no production local handlers by design and therefore fails closed until canary integration.
- SQLite initializes from `multi_pc/schema.sql`. Production should migrate the constraints to PostgreSQL before multi-instance scaling.

## Production boundaries verified

- No active-runtime file under `D:\Highlight_Video_Studio` was read for modification or changed.
- No VPS, DNS, Caddy, Basic Auth, scheduler, router, or tunnel setting was changed.
- No credential or object-storage requirement was added.
- No application version or release tag was changed.
- The existing v1.0.19 app and reverse-tunnel trial remain separate from this skeleton.

## Phase 2 / canary handoff

1. Implement a DPAPI/Credential Manager device store and credential revoke/rotation.
2. Add a durable local execution-receipt ledger keyed by cloud `job_id` before wiring non-idempotent publication.
3. Register narrow local handlers around existing download/transcript/render and Zernio paths; validate URLs and resolve all secrets locally.
4. Add secure-cookie browser sessions, CSRF, login throttling, account lifecycle, audit logs, retention, PostgreSQL migrations, monitoring, and proxy body/rate limits.
5. Build account/device/job UI and run a one-PC canary while Basic Auth/tunnel stays available for rollback.
6. Remove Basic Auth and disable the reverse tunnel only in a coordinated cutover after app-native auth and isolation review pass.
7. Optionally add direct signed object-storage uploads with bounded object key, method, size, expiry, checksum, and no VPS media proxy.

## Expected resource profile

- VPS: metadata JSON and DB operations only; no downloads, Whisper, FFmpeg, GPU, browser automation, or media storage.
- Connector idle target: low CPU and roughly sub-100 MB Python runtime; one active device job prevents render oversubscription.
- Heartbeat target: 15–30 seconds/device in production. Current polling scaffold defaults to 5 seconds and should gain jitter/long-poll or WebSocket fallback before large rollout.
- Media paths remain source → PC and, if later enabled, PC → object storage directly.
