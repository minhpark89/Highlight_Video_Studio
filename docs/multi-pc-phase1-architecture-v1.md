# Highlight Video Studio local-first desktop architecture — Phase 1 v3

- **Spec version:** `2026-09-28.phase1-v3-local-mvp`
- **Supersedes:** `2026-09-28.phase1-v2-local-desktop`, `2026-09-28.phase1` (cloud-first control plane)
- **Status:** 1-PC offline MVP implemented and verified; cloud deferred to Phase 2
- **Preview build:** `1.0.19-preview.1` (`highlight-desktop-offline-preview`)
- **Public product target:** `https://highlight.shopkitai.com` (account/licence/update only)
- **Compatibility boundary:** existing `APP_VERSION = "1.0.19"` and release tags are unchanged.

## 0. MVP status

Delivered and verified on this PC: real hardware probe plus FFmpeg canary encodes, a loopback-only
desktop launcher with per-run session auth, a non-destructive side-by-side installer, an executed
render canary (NVENC verified), and SHA256-pinned artifacts. Details and evidence are in
`docs/multi-pc-phase1-checkpoint-2026-09-28.md`; install/startup/update/migration design is in
`docs/desktop-preview-install-startup-update.md`. The cloud control plane, connector and licence
work described below remain Phase 2 and are not required for the preview to render locally.

## 1. Decision summary

The product is an **installed local desktop app per PC**. Each PC owns the UI, backend, pipeline, secrets, browser profiles, media, and rendering. No inbound port is opened, no router change is required, and no browser-dependent remote app is used for normal work.

Cloud is deliberately small and optional: login/licence activation, update checks/notifications, and optional lightweight sync of job metadata or multi-device coordination. When the cloud is unreachable, the app still starts and renders locally; only login-dependent or sync features degrade.

Consequences that shape the rest of this document:

- The desktop shell calls the local backend **in-process** where possible. Basic Auth becomes local session/token auth, not public browser auth.
- If the existing Flask app must stay for a transition period, it binds loopback only on an isolated or random port with local auth, and is never published.
- Hardware is detected and benchmarked, and a safe render profile is derived and cached locally; device names alone are never trusted.
- Video and large media never leave the PC in Phase 1. An optional direct-to-object-storage upload interface may be added later without routing bytes through the cloud.

## 2. Current Flask route/data audit

The current `web/app.py` is a single-machine trusted-local application with 55 routes and background workers. It combines UI, orchestration, local files, secrets, external account state, rendering, and publishing. It is the application core that becomes the **local backend**; it must never be moved wholesale to the cloud.

| Current route groups | Data/side effects | Local-first placement |
|---|---|---|
| `/`, `/api/system/info` | UI shell, non-sensitive version/capability summary | Desktop shell owns the main window. Local backend may serve the shell during transition; version and coarse capability data can be synced as metadata. |
| `/api/jobs*`, `/api/queue/*` | URLs, job state, retries/cancel, local pipeline execution | Local backend only. Optional cloud copy stores device id, action name, state, coarse progress and a local output reference. |
| `/api/clips*` | Local filenames, media playback/delete, posted ledger | Local only. Cloud may receive opaque local output reference plus size/duration/status, never media bytes. |
| `/api/research*` | External search results, saved research | Local execution. Optional sanitized metadata sync only. |
| `/api/settings`, `/api/llm/*`, `/api/image-provider/*`, `/api/content/*` | API endpoints/keys, model probes, generated assets | Local only, stored in a protected local store. Never uploaded, never echoed to a browser or cloud job payload. |
| `/api/system/youtube_status`, `/api/system/open_chrome` | Chrome cookie DB and local process launch | Local only. Invoked by the desktop shell with local confirmation; never remotely reachable. |
| `/api/tokens*`, `/api/token-groups*`, `/api/pages*`, `/api/groups*` | Meta page tokens, page bindings, vault state | Local only. Cloud may store user-authored opaque destination labels, not page tokens or raw vault records. |
| `/api/publish/reel`, `/api/distribute/batch`, `/api/posts*`, `/api/schedule/rules` | Facebook/Zernio credentials, schedules, publish side effects | Local only. Publication runs on the PC and returns a sanitized receipt; approval gates stay local. |
| `/api/website-config*`, `/api/website/publish_draft` | CMS password, SSH path/config, upload and public publish | Local only. Disabled in the Phase 1 local adapter until explicitly enabled. |

Sensitive persisted files include `config.json`, website configuration, token vault/page binding files, Chrome profiles/cookies, downloads/output/temp, transcript data, posts/ledgers, and pending first-comment tokens. Local masking in `public_config()` is not a security boundary; the boundary is that these files and routes are only ever reachable inside the PC.

## 3. Components and trust boundaries

1. **Desktop shell (local UI)** — packaged window (WebView/embedded browser or native UI) that talks to the local backend in-process or over a loopback-only endpoint with a per-run session token. Not a public web app.
2. **Local backend** — the existing Flask/pipeline core plus new local services (hardware probe, profile cache, job scheduler, local ledger, publish pipeline). Owns all secrets and media.
3. **Safe local adapter** — `multi_pc/adapter.py`; only registered Python callables for the fixed action set; no command string, shell, `eval`, arbitrary import, or generic RPC. Used for both local UI dispatch and optional cloud metadata jobs.
4. **Hardware benchmark service** — `multi_pc/hardware.py`; detects GPU/CPU/RAM/disk and encoder availability, runs a short canary encode, derives a safe render profile.
5. **Profile cache** — `multi_pc/profile_cache.py`; caches the derived profile, invalidates on hardware/driver fingerprint change or TTL expiry.
6. **Optional cloud control plane** — `multi_pc/control_plane.py`; accounts/sessions, device registry, licence, update metadata, small job-metadata queue, heartbeat/progress. No rendering, transcription, downloads, or media.
7. **Optional sync connector** — `multi_pc/connector.py`; outbound HTTPS only, no inbound listener, exponential reconnect, continues local work while offline.
8. **Optional object storage** — disabled interface only, for a later direct PC→storage artifact upload; no storage credentials or bytes pass through the cloud.

## 4. Desktop packaging, startup, and update design

**Packaging**

- Ship a signed installer (MSI/EXE) that bundles: desktop shell, local backend, Python runtime, FFmpeg/ffprobe, yt-dlp/node, Whisper model, and default config.
- User data lives outside the install directory under `%LOCALAPPDATA%\HighlightVideoStudio` (or `D:\Highlight_Video_Studio\data` for the current operator layout): jobs, ledgers, outputs, downloads, temp, profiles, caches.
- Secrets use Windows DPAPI/Credential Manager with per-user ACLs. No plaintext credential files, no secrets in the installer or command line.

**Startup**

1. Single-instance guard (named mutex) prevents duplicate backends.
2. Local backend starts on an **isolated loopback port** chosen from a free/random port and written to a per-user runtime file with an ACL, or serves through an in-process channel that needs no TCP port at all. Port 5080 belongs to production and is refused outright.
3. A per-run session token is generated locally for shell↔backend calls; it is never a fixed shared secret and is never sent anywhere external.
4. Hardware probe + canary run in the background; the app is usable immediately with a conservative default profile.
5. Cloud licensing/sync initializes asynchronously and never blocks the UI.

Implemented in `multi_pc/local_launcher.py` and `run_local.py`: `pick_free_port()` asks the OS for an
ephemeral port, `SessionGuard` enforces loopback-only + token on every request (`/healthz` exempt),
and `runtime.json` carries host/port/token for the shell, removed on shutdown.

**Update**

- Update check is an outbound signed request to the cloud (version manifest, channel, hashes, signature).
- Download happens in the background; installation is user-confirmed and never silent.
- Updates are signed and verified; a rollback/side-by-side previous version is retained.
- If the cloud is unavailable, the app runs on the installed version and retries later.

## 5. Hardware detection, benchmarking, and render profile

**Detection** (`multi_pc/hardware.py`)

- GPU: vendor/model/VRAM/driver via vendor tooling (e.g. `nvidia-smi` query with structured output).
- CPU: logical and physical cores; RAM via OS APIs.
- Disk: free space on the output/temp volume plus a short write-throughput probe.
- Encoders: enumerate FFmpeg encoders (`-encoders`) to learn NVENC/QSV/AMF/libx264 availability.

**Verification before trust**

- Listing an encoder is not proof it works. A short **canary encode** (a real 2 s 1080p30 synthetic clip) is attempted per candidate in the order **NVENC → QSV → AMF → CPU**, and each artifact is validated with `ffprobe -count_frames`.
- The first candidate whose encode succeeds *and* whose artifact decodes as a 1080p stream is selected. A failing canary demotes that encoder without failing the app.
- Observed on this PC: FFmpeg 8.1.2 lists `h264_qsv` and `h264_amf`, but both canaries failed (no Intel iGPU, no AMD GPU), so NVENC was selected. Name-list checks alone would have been wrong.

**Derived profile** (`derive_render_profile`)

- Selected encoder, whether hardware decode is used, max concurrent renders, a RAM budget, and human-readable notes.
- Safe defaults: serialized (concurrency 1) for CPU fallback or low RAM; concurrency raised only for strong CPU/RAM plus a verified hardware encoder.
- Low free disk space adds a purge/rotate warning to the profile notes.

**Caching and re-probe** (`multi_pc/profile_cache.py`)

- The profile is cached locally with a hardware/driver fingerprint and a TTL (default 7 days).
- The cache is invalidated when the fingerprint changes, for example after a GPU driver update, GPU swap, RAM/CPU change, or OS platform change.
- A manual "re-detect" action is always available; forced re-probe bypasses the cache.

## 6. Threat model

| Threat | Phase 1 control |
|---|---|
| Remote access to a customer PC | No inbound port, no router change, no reverse tunnel. Backend is loopback-only or in-process; the optional connector is outbound HTTPS only. |
| Local network pivot to the app | Loopback-only bind plus per-run local session token; no published 5080; no browser Basic Auth credential to steal or spray. |
| Cross-account/device access (cloud) | Every cloud query scopes by `account_id`; device credentials resolve exactly one device; leases filter by that device. Tests cover both boundaries. |
| Pairing-code theft/replay | Random code, hashed at rest, short TTL, single transaction, consumed once, created only by an authenticated account. |
| Cloud database theft | Passwords use PBKDF2; session/device/pairing tokens are SHA-256 digests. Production needs encrypted disks, backups, and managed DB access. |
| Device-credential theft on PC | Protected-store boundary refuses plaintext save; Windows packaging must implement DPAPI/Credential Manager with ACLs. Revocation/rotation is Phase 2. |
| Job injection/RCE | Fixed action allowlist, fixed per-action payload fields, structured callable dispatch only. Unknown fields/actions fail closed. |
| Secret exfiltration to cloud | Sensitive field names are rejected; bearer/key-like values are redacted from progress/results/errors. Cloud contracts never request local credentials. |
| Malicious source URLs / SSRF | Local handlers validate allowed schemes/providers and never let a cloud payload select arbitrary internal endpoints. Cloud never fetches source URLs. |
| Overload on weak hardware | Benchmark-derived concurrency and RAM bounds; CPU fallback forced to concurrency 1; low disk/RAM produce explicit warnings. |
| Licence/sync outage | Local render path never depends on cloud availability; cloud failure pauses only login-gated or sync features. |
| Large-media transit/cost exhaustion | Job JSON is metadata only; no cloud upload endpoint; media stays local. If storage sync is enabled later, uploads go PC→storage directly with bounded size/method/expiry. |
| Data retention | Local ledgers, logs, and caches need retention/pruning policy; cloud metadata is minimal and deletable per account/device. |

## 7. Cloud API contract (small, optional)

All production endpoints are HTTPS JSON under `/v1`. Cloud authentication and device authentication are separate credentials.

| Method/path | Principal | Contract |
|---|---|---|
| `GET /health` | public | Process/DB readiness and API version; no customer data. |
| `POST /v1/auth/register` | public/admin-gated | Scaffolding; disabled by default. |
| `POST /v1/auth/login` | public | Short-lived session once, `Cache-Control: no-store`. |
| `POST /v1/auth/logout` | account | Revokes current session. |
| `POST /v1/devices/pairing-codes` | account | Single-use code plus expiry. |
| `POST /v1/devices/pair` | unpaired device | `{code,name,fingerprint}` → device id and credential once. |
| `GET /v1/devices` | account | Owned devices and coarse online timestamps only. |
| `POST /v1/device/heartbeat` | device | Coarse capabilities/version/profile summary; no secrets or media. |
| `POST /v1/jobs` | account | Requires `Idempotency-Key`; `{device_id,action,payload}`; device must be owned. |
| `GET /v1/jobs/{id}` | account | Owned job metadata/status only. |
| `POST /v1/device/jobs/lease` | device | No content, or that device's active/new job plus lease. |
| `POST /v1/device/jobs/{id}/progress` | device lease | `{lease_id,progress}`; renews lease. |
| `POST /v1/device/jobs/{id}/complete` | device lease | `{lease_id,status,result,error}`; terminal and replay-safe. |

Allowlisted `highlight_pipeline` payload fields: `source_url`, `title`, `options`, `client_job_ref`. Allowlisted `publish_zernio` fields: `local_output_ref`, `destination_ref`, `caption`, `schedule_at`. Local config resolves credentials and account bindings; cloud never sees them.

Proposed, not implemented: licence/entitlement endpoints (`/v1/licence/activate|refresh`), update manifest endpoint, and `/v1/jobs/{id}/artifacts/upload-intent` returning a single-object, single-method, short-lived, size-bounded URL for direct PC→storage upload.

## 8. Database and state machine

Executable SQLite DDL for the **optional cloud** is in `multi_pc/schema.sql`: `accounts`, `sessions`, `pairing_codes`, `devices`, `jobs`. SQLite is suitable for a single control-plane process; migrate the same constraints to PostgreSQL before horizontal scaling. The local backend keeps its own ledgers (jobs, posted clips, publish receipts, profile cache) locally.

Job metadata state machine:

```text
queued -> leased -> running -> succeeded
   ^         |          |  \-> failed
   |         |          \----> cancelled (future account action)
   +---------+ lease expiry/reconnect reclaim (new lease_id, attempt + 1)
```

Invariants:

- `(account_id, idempotency_key)` is unique; repeated creation returns the stored job.
- A device sees only jobs whose `device_id` matches its credential.
- Repeated lease during an unexpired lease returns the same `lease_id`; attempt is unchanged.
- Expired lease is reclaimable; stale lease progress/completion is rejected.
- Repeated terminal completion with the same lease returns the stored terminal result.
- Connector failure before acknowledged completion leaves the job non-terminal; local work continues and sync retries.
- The **local** ledger keyed by a stable job/action id prevents duplicate non-idempotent work (for example double publish) across reconnect or reclaim.
- Cloud unavailability never blocks local job creation or rendering.

## 9. Migration, cutover, and rollback

1. Keep v1.0.19 local service, its `HighlightVideoStudio_5080` supervisor, and the Basic-Auth reverse-tunnel trial unchanged while building the desktop package.
2. Build the desktop shell + local backend against a **copy** of the pipeline. Do not modify the running install.
3. Move secrets to DPAPI/Credential Manager and replace browser Basic Auth with local session auth for shell↔backend calls.
4. Ship a signed installer with side-by-side or per-user install so an existing install is untouched until the user migrates.
5. Migrate data by copying (not moving) jobs/ledgers/config into the new user-data location; run the first launch read-only against media, then enable writes after verification.
6. Once the desktop app is verified on a canary PC, retire the reverse tunnel and any public publishing of the local app. Never overlap a public unauthenticated window.
7. Rollback: stop the desktop app, keep the old install and tunnel guidance available, and continue on v1.0.19. Local data is unchanged because migration copies rather than moves.

## 10. Resource/performance expectations

- **Cloud:** typical request/response bodies under tens of KB; heartbeat every few minutes per online device; optional job metadata only. No FFmpeg, Whisper, download, browser automation, or media disk usage.
- **Local backend:** idle memory dominated by the existing runtime; negligible CPU when idle; one active job per device by default, with benchmark-derived concurrency above that.
- **Hardware probe:** a few seconds of structured tooling calls plus one short canary encode per candidate encoder; runs in the background and is cached.
- **Disk:** benchmark and profile need room for a ~64 MB temporary probe and short canary outputs, both cleaned up.
- **Network:** source downloads go source → PC. No media to cloud in Phase 1; optional later storage sync goes PC → object storage directly.

## 11. Phase 2 backlog

- Desktop shell implementation (WebView/native), installer signing, per-user ACLs, DPAPI credential store, single-instance and crash-recovery design.
- Local session auth replacing Basic Auth; local approval gates preserved.
- Production local adapters for the existing pipeline and Zernio with URL validation and local consent.
- Cloud licence/entitlement service, update manifest and delta update, device revoke/rotate.
- Durable local execution-receipt ledger keyed by job/action id.
- Optional direct object-storage artifacts with bounded key/method/size/expiry/checksum.
- PostgreSQL migrations, audit events, rate limits, metrics, retention, admin support tooling.
- Hardware coverage expansion: additional AMD/Intel detection paths, multi-GPU policy, thermal/power throttling awareness.
