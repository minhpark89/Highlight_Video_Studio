# Highlight Studio v1.0.19 PC trial handoff

## Scope and checkpoint

- PC runtime: `D:\Highlight_Video_Studio`
- Source repository: `D:\Highlight_Video_Studio_v1015`
- Application version remains `1.0.19`; `APP_VERSION` was not changed.
- Existing scheduled task `HighlightVideoStudio_5080` remains the application supervisor.
- No router/public port is opened. Waitress defaults to `127.0.0.1:5080`.
- The reverse SSH endpoint is fixed to VPS loopback: `127.0.0.1:15080` -> PC `127.0.0.1:5080` over SSH alias `vps`.
- Pending VPS/DNS/Caddy/TLS/auth work remains owned by `task_4e2b9ac158b6` (`bob_vps`).

## Installed but inactive

- `ops\highlight_reverse_tunnel.ps1`: lightweight reconnecting SSH supervisor with a PID lock, local app readiness check, keepalives, and loopback-only `-R` forwarding.
- `ops\register_highlight_tunnel_task.ps1`: explicit registration/removal helper.
- No `HighlightVideoStudio_ReverseTunnel` scheduled task is created during PC preparation.

## Activation after VPS owner is ready

Run from an elevated PowerShell prompt only after `task_4e2b9ac158b6` confirms the VPS loopback listener/proxy is ready:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Highlight_Video_Studio\ops\register_highlight_tunnel_task.ps1" -Register
Start-ScheduledTask -TaskName HighlightVideoStudio_ReverseTunnel
```

Verify on the PC:

```powershell
Get-ScheduledTask -TaskName HighlightVideoStudio_5080,HighlightVideoStudio_ReverseTunnel
Get-Content "D:\Highlight_Video_Studio\ops\state\highlight_reverse_tunnel.log" -Tail 30
```

The VPS owner must independently verify that `127.0.0.1:15080` is loopback-only and reaches app version `1.0.19` before enabling Caddy traffic.

## Rollback

Tunnel only (does not alter the application task):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Highlight_Video_Studio\ops\register_highlight_tunnel_task.ps1" -Unregister
```

Application bind rollback, only if explicitly approved: restore the prior bind lines in `web\app.py` and `run_server.py`, then restart only the Highlight backend. Do not open a router port as a fallback.

## Security design

The application accepts connections only on PC loopback by default. The PC initiates an outbound SSH session. The remote forward requests a listener only on VPS loopback, so Caddy can consume it locally without exposing port `15080`. SSH uses batch mode, fails closed if forwarding cannot be established, and exits after failed keepalives so the supervisor can reconnect. Public HTTPS and authentication remain separate VPS-side gates.
