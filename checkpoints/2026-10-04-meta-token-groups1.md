# Highlight 1.1.9 — Meta schedules, parallel publishing and Token/Page groups

The app supports 1, 2, 4 or 8 publishing workers (default 4, maximum 8). The setting is persisted independently of render concurrency and is exposed in Token Management, Post Management and both scheduling dialogs. Due app posts and queued Meta handoffs run in parallel across distinct credentials; each Token/Page has at most one active upload. Per-token spacing and Meta usage/cooldown gates remain enabled.

Workers load an independent posts-store revision, persist upload identity before transfer/finish, and merge only changed fields. Shared clips are removed only after every queued Page has confirmed publication. Queue/history, First Comments and concurrent Content Studio metadata are preserved.

Scheduling dialogs expose App-held and Meta-held modes before confirmation. Batch Meta mode prepares Website/First Comment content before requesting a handoff. If its native scheduling window expires, the app reports a failure and asks for a new schedule instead of silently posting through the app. First Comment still requires the app after the scheduled publication time.

Token groups refresh immediately after creation. Token import can choose an existing group or create a named group; ungrouped tokens are labelled explicitly. Creation synchronizes each selected credential independently, snapshots Pages from a chosen source or the verified pool, and can create a linked Page group. Group allocation persists one verified credential per Page in `page_token_bindings`; new posts honor that assignment even when another group changes the Page's default credential. Existing queued credentials are never rebound. Page filters use group Page snapshots and management dialogs fetch current lists/counts.

Verification: Python compilation, the complete regression suite, and an isolated browser smoke test covering fresh groups, linked Page selectors, saved worker counts and both batch modes. Browser network was intercepted; no test uploaded a real Reel or changed live credentials. Detailed evidence is kept under `E:\OPENCLAW\BOB\support\meta-token-groups1\evidence`.

Deployment uses the actual installer extraction/preservation code, only when Meta publishing/processing and render active/running are zero. Preserve queue, Vault, Pages/groups, content packages, comments, profiles, config and render pause state. Do not resume paused render jobs or convert existing app schedules.

Release/deployment identities and final verification are appended after packaging and installation. The previous release and private backups remain available.

Slow Meta processing continues to be checked read-only after six attempts, with a five-minute interval. A confirmed upload is never replayed. This addresses the observed `upload_complete` / `processing not_started` object that the previous runtime stopped checking after attempt six.
