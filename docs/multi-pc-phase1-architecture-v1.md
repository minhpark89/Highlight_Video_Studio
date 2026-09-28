# Highlight Video Studio multi-PC architecture — Phase 1 v1

- **Spec version:** `2026-09-28.phase1`
- **Status:** runnable skeleton, not deployed
- **Public product target:** `https://highlight.shopkitai.com`
- **Compatibility boundary:** existing `APP_VERSION = "1.0.19"` and release tags are unchanged.

## 1. Decision summary

Phase 1 replaces the one-PC reverse-SSH trial with a cloud control plane and outbound-only PC connectors. The browser talks only to the control plane. Each connector opens outbound HTTPS requests, leases jobs assigned to its device, and invokes an allowlisted Python adapter around local functionality. No PC listener is made public, port 5080 remains loopback-only, and video bytes never pass through the VPS.

The VPS stores identities, sessions, devices, small job requests, state, progress, and local artifact references. A customer PC keeps source credentials, browser profiles, cookies, API keys, downloads, transcripts, media, FFmpeg/GPU execution, and publication integrations.

## 2. Current Flask route/data audit

The current `web/app.py` is a single-machine trusted-local application with 55 routes and background workers. It combines UI, orchestration, local files, secrets, external account state, rendering, and publishing. It must **not** be moved wholesale to the VPS.

| Current route groups | Data/side effects | Phase 1 placement |
|---|---|---|
| `/`, `/api/system/info` | UI shell, non-sensitive version/capability summary | New public UI/control plane may serve its own shell and coarse device metadata. Existing local UI stays local during migration. |
| `/api/jobs*`, `/api/queue/*` | URLs, job state, retries/cancel, local pipeline execution | Cloud: selected device, allowlisted action, small sanitized request, state/progress. Local: execution, detailed logs, transcript, paths, media. |
| `/api/clips*` | Local filenames, media playback/delete, posted ledger | Local only. Cloud may receive opaque local output reference plus size/duration/status, never media bytes. |
| `/api/research*` | External search results, saved research | Local execution. Optional sanitized result metadata can be cloud job progress in a later contract. |
| `/api/settings`, `/api/llm/*`, `/api/image-provider/*`, `/api/content/*` | API endpoints/keys, model probes, generated assets | Local only. Source keys and provider responses that may echo credentials never enter cloud/browser job payloads. |
| `/api/system/youtube_status`, `/api/system/open_chrome` | Chrome cookie DB and local process launch | Local only; never remotely expose these routes. A future adapter action needs a narrow explicit contract and local confirmation policy. |
| `/api/tokens*`, `/api/token-groups*`, `/api/pages*`, `/api/groups*` | Meta page tokens, page bindings, vault state | Local only. Cloud may store user-authored opaque destination labels, not page tokens or raw vault records. |
| `/api/publish/reel`, `/api/distribute/batch`, `/api/posts*`, `/api/schedule/rules` | Facebook/Zernio credentials, schedules, publish side effects | Local only. Phase 1 adapter allowlists `publish_zernio`; execution uses local configuration and returns sanitized receipt metadata. |
| `/api/website-config*`, `/api/website/publish_draft` | CMS password, SSH path/config, upload and public publish | Local only. Not enabled by the Phase 1 adapter. |

Sensitive persisted files include `config.json`, website configuration, token vault/page binding files, Chrome profiles/cookies, downloads/output/temp, transcript data, posts/ledgers, and pending first-comment tokens. The existing `public_config()` masking is useful for a local UI but is not a sufficient cloud boundary because many mutation/probe routes still accept secrets.

## 3. Components and trust boundaries

1. **Public web UI** — app-native login/session; lists owned devices and submits metadata-only jobs to a selected device.
2. **Control plane** — Flask skeleton in `multi_pc/control_plane.py`; account/session authentication, one-time pairing, registry, queue, lease, heartbeat, progress, completion.
3. **Connector** — `multi_pc/connector.py`; outbound HTTPS polling, no inbound listener, exponential reconnect, one active lease per device.
4. **Safe local adapter** — `multi_pc/adapter.py`; only registered Python callables for `highlight_pipeline` and `publish_zernio`; no command string, shell, `eval`, arbitrary import, or generic RPC.
5. **Existing local app/pipeline** — remains untouched in Phase 1. A later integration handler translates the adapter payload to existing pipeline calls and local ledgers.
6. **Optional object storage** — disabled interface only: the control plane may later issue a short-lived, content-length-limited signed upload URL directly to the PC. The PC uploads directly to object storage; no object credentials or bytes pass through the VPS.

## 4. Threat model

| Threat | Phase 1 control |
|---|---|
| Cross-account/device access | Every account query scopes by `account_id`; device credentials resolve one device; leases filter by that device. Tests cover both boundaries. |
| Pairing-code theft/replay | Random code, hash at rest, short TTL, single transaction, consumed once. Browser must be authenticated to create it. |
| Database theft | Passwords use PBKDF2; session/device/pairing tokens are SHA-256 digests. Raw bearer values are returned once. Production still needs encrypted disks/backups and managed DB access. |
| Connector credential theft | Phase 1 defines a protected-store boundary and refuses plaintext save. Windows packaging must implement DPAPI/Credential Manager with ACLs. Revocation/rotation is Phase 2. |
| Job injection/RCE | Fixed action allowlist, fixed per-action payload fields, structured callable dispatch only. Unknown fields/actions fail closed. |
| Secret exfiltration | Sensitive field names are rejected; bearer/key-like values are redacted from progress/results/errors; cloud contracts never request local source credentials. |
| Lease duplication/network partition | One unexpired active lease per device; repeated lease returns the same lease; expired work is reclaimed with a new lease and incremented attempt. Completion is idempotent per lease. Local handlers must use `job_id` as their operation ledger key. |
| Large-media transit/cost exhaustion | Job JSON is metadata only. No upload endpoint exists. Reverse proxy must enforce small JSON body limits before cutover. |
| Session theft/CSRF | Skeleton uses bearer sessions with expiry and explicit logout. Production browser delivery should use Secure, HttpOnly, SameSite cookies plus CSRF tokens; do not place bearer tokens in localStorage. |
| Malicious URLs/SSRF | Connector-local handlers must validate allowed schemes/providers and never let cloud payloads select arbitrary internal endpoints. Control plane does not fetch source URLs. |
| Public endpoint abuse | TLS, rate limiting, login throttling, audit logging, and generic auth errors are required at deployment. No Basic Auth removal until these gates pass. |

## 5. API contract

All production endpoints are HTTPS JSON under `/v1`. Browser account authentication and device authentication use separate credentials. The skeleton uses bearer headers for testability; production browser sessions should be moved to secure cookies without changing resource authorization.

| Method/path | Principal | Contract |
|---|---|---|
| `GET /health` | public | Process/DB readiness and API version; no customer data. |
| `POST /v1/auth/register` | public/admin-gated | Scaffolding only; disabled by default. `{email,password}`. |
| `POST /v1/auth/login` | public | Returns short-lived session once with `Cache-Control: no-store`. |
| `POST /v1/auth/logout` | account | Revokes current session. |
| `POST /v1/devices/pairing-codes` | account | Returns single-use code and expiry. |
| `POST /v1/devices/pair` | unpaired connector | `{code,name,fingerprint}` → device id and credential once. |
| `GET /v1/devices` | account | Owned devices and coarse online timestamps only. |
| `POST /v1/device/heartbeat` | device | Sanitized capabilities; updates liveness. |
| `POST /v1/jobs` | account | Requires `Idempotency-Key`; `{device_id,action,payload}`. Device must be owned. |
| `GET /v1/jobs/{id}` | account | Owned job metadata/status only. |
| `POST /v1/device/jobs/lease` | device | Returns no content or that device's active/new job and lease. |
| `POST /v1/device/jobs/{id}/progress` | device lease | `{lease_id,progress}`; renews lease and marks running. |
| `POST /v1/device/jobs/{id}/complete` | device lease | `{lease_id,status,result,error}`; terminal and replay-safe. |

Allowlisted `highlight_pipeline` payload fields: `source_url`, `title`, `options`, `client_job_ref`. Allowlisted `publish_zernio` fields: `local_output_ref`, `destination_ref`, `caption`, `schedule_at`. These are metadata; local config resolves actual credentials and account bindings.

Proposed, not implemented object-storage extension: `POST /v1/jobs/{id}/artifacts/upload-intent` returns `{method,url,headers,expires_at,max_bytes,object_ref}` only when the account enables storage. URL is single-object/single-method, expires in minutes, and is consumed directly by the connector. Completion reports `object_ref` and checksum, never storage credentials.

## 6. Database and state machine

Executable SQLite DDL is in `multi_pc/schema.sql`: `accounts`, `sessions`, `pairing_codes`, `devices`, and `jobs`. SQLite is suitable for a skeleton/single control-plane process; production should migrate the same constraints to PostgreSQL before horizontal workers.

Job state machine:

```text
queued -> leased -> running -> succeeded
   ^         |          |  \-> failed
   |         |          \----> cancelled (future account action)
   +---------+ lease expiry/reconnect reclaim (new lease_id, attempt + 1)
```

Invariants:

- `(account_id, idempotency_key)` is unique.
- A device sees only jobs whose `device_id` matches its credential.
- Repeated lease during an unexpired lease returns the same `lease_id` without incrementing attempt.
- Expired lease is reclaimable; stale lease progress/completion is rejected.
- Repeated terminal completion using the same lease returns the stored terminal result.
- Connector failure before acknowledged completion leaves the job non-terminal; it is retried after expiry.
- Local execution must keep its own `job_id`/action receipt so a reclaimed job can return a prior result rather than repeat non-idempotent publication.

## 7. Migration, cutover, and rollback

1. Keep v1.0.19 local service and Basic-Auth reverse-tunnel trial unchanged while building the parallel control plane.
2. Deploy the control plane privately/staging with registration disabled; create test accounts administratively, enable TLS, rate/body limits, secure cookie sessions, logs, backups, and monitoring.
3. Install a separately supervised connector canary on one PC. Pair it using a short-lived code. Do not modify the existing 5080 supervisor.
4. Add a narrow `highlight_pipeline` integration handler and local idempotency ledger. Run synthetic/small jobs; confirm media remains local and VPS CPU/disk/network stay metadata-only.
5. Add public UI account/device/job screens. Run account isolation, reconnect, revoked-device, and load tests.
6. Cut traffic to app-native auth only after session/CSRF/rate-limit review. Then remove browser Basic Auth and disable/remove the reverse tunnel. Never overlap a public unauthenticated window.
7. Rollback: restore Basic Auth proxy route to the old loopback reverse-tunnel target, stop accepting new control-plane jobs, allow/abort leased metadata jobs, and stop the connector. Local v1.0.19 and its data remain intact throughout.

## 8. Resource/performance expectations

- **VPS:** typical request/response bodies under tens of KB; heartbeat every 15–30 seconds per online device; long-poll/WebSocket can replace 5-second polling in Phase 2. No FFmpeg, Whisper, download, browser automation, or media disk usage.
- **PC connector:** idle memory target below roughly 100 MB Python runtime; negligible CPU while polling; pipeline retains existing GPU/CPU/RAM/disk requirements. One active job per device in the skeleton prevents local resource oversubscription.
- **Database:** indexes support per-device queue and token lookup. SQLite write serialization is acceptable for development, not a many-tenant production target.
- **Network:** metadata only in Phase 1. Source downloads go source → PC; optional future artifacts go PC → object storage directly.

## 9. Phase 2 backlog

- Secure-cookie browser session/CSRF and email verification/password reset/MFA path.
- Device revoke/rotate, DPAPI/Credential Manager implementation, signed connector update, and per-device version policy.
- PostgreSQL migrations, audit events, rate limits, metrics, tracing, cleanup/retention, admin support tooling.
- Long polling or WebSocket with fallback, lease jitter, graceful shutdown, and local durable execution receipt ledger.
- Production adapters for existing pipeline and Zernio with URL validation and local consent/approval rules.
- Public UI, optional direct object-storage artifacts, download authorization, quotas/billing, and multi-region considerations.
