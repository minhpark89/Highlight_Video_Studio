# CODEX CHECKPOINT — Highlight Desktop Test v1.1.9-autopublish4

Updated: 2026-10-05 10:23 Asia/Saigon. Branch: `release/v1.1.9`.

## Public release

- Packaged source commit: `181b05236687d92cfb5f1eaf46f90f1c28807bc6`.
- Tag: `v1.1.9-autopublish4` (new immutable revision).
- Installer bytes: `704499712`.
- SHA-256: `62396dabd0774359cb923e34a42358144e5edf9a109c13141591a15570251285`.
- Release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.1.9-autopublish4
- Installer: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.1.9-autopublish4/Highlight_Desktop_Test_Setup_v1.1.9-autopublish4.exe
- Public download verification is recorded in local `release/autopublish4_release.json` and `E:/OPENCLAW/BOB/CODEX_CHECKPOINT_LATEST.md` after publication. This asset records the state before publication.

## State safety

The controlled install preserved 26 mutable files and all 400 post records. Existing Meta upload IDs, Page IDs, original Token IDs, article URLs, package IDs and First Comment snapshots were checked before and after install. No new Meta upload was issued.

## Live proof

The installed app was observed at `http://127.0.0.1:51414` after restart. Scheduler thread was alive with a successful last cycle. Numeric UI controls persisted custom values 7 (publishing) and 6 (Content/LLM) through reload; invalid 33 and 2.5 were rejected. Settings were restored to posting 8 and Content/LLM 4. The recovery modal exposed the same-ID action and 31 verified credential choices.

Read-only final audit at `2026-10-05T10:23:36+07:00`: **398/400 posts published, 398 First Comments posted**. Eleven previously recovered posts and eleven comments were independently read back through Meta API. All 400 original records, article URLs, Page/Token IDs and package IDs were preserved, together with 303 pre-existing upload IDs, 138 video IDs and 388 pre-existing post IDs. This supersedes any assumption that refreshing the Page token alone resolves the two identity rejections.

The two outstanding objects on Page `1366749239846014` were each tested through the installed recovery endpoint using the original Token and a different verified Token. Both calls refreshed the Page token, re-read the same object, and returned Meta's identity requirement `368 / 4854002`; the upload IDs remained unchanged. The user must complete Facebook identity confirmation. Automatic retry remains enabled with backoff.

| Local post | Existing Meta ID | Result |
| --- | --- | --- |
| `post_1791121129_7e1a6d` | `1373334701223226` | Complete upload; Finish still rejected by Meta identity check |
| `post_1791121324_dae163` | `1722433486142952` | Ready, native schedule still held; publish rejected by Meta identity check |

Original publishing Token ID remains `tok_1791016027_24`. The explicit same-Page recovery credential is recorded separately as `meta_recovery_token_id=tok_1791016031_29` (owner Autopost 25); it also passed ACTIVE, VERIFIED and CREATE_CONTENT. Future automatic reconciliation and comment requests use that explicit binding without changing the original Token ID.

Read-only live audit: `python support/autopublish4/tools/final_live_audit.py http://127.0.0.1:51414`. Rediscover the port after a later restart. Never rerun migration/repair scripts against active workers.

## Verification

- Tests: **482 passed, 3 skipped, 29 subtests passed**.
- Payload verification: success, 8,006 entries, no runtime state or credential seeds.
- UI evidence and same-ID recovery evidence are under `support/autopublish4/evidence/`.
- Exact files: `payload_verify.json`, `install_preservation.json`, `live_ui_verify.json`, `recovery_original.json`, `recovery_alternative.json`, `final_live_audit.json`. Evidence contains no raw access tokens.
- `git diff --check` passed before commit; source commit is clean and payload source identity is clean.

Next check: after Meta identity confirmation, inspect the two IDs through the dashboard and confirm `published` plus First Comment `posted`. Do not upload either video again.
