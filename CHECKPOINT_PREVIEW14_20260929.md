# Highlight Video Studio preview.14 checkpoint — 2026-09-29

## Source

- Canonical worktree: `F:\openclaw\.openclaw\workspace\worktrees\highlight-multi-pc`
- Branch: `feature/multi-pc-control-plane`
- Fix commits: `ea3c4a2` and `092e1f5`
- Runtime/generated files intentionally excluded: `posts.json`, `data/content_packages.json`, `data/run/`, `run/`.

## Fixes in preview.14

- Scheduling rejects invalid `schedule_time` with an explicit 400 instead of falling through to immediate publish.
- Ordinary reel scheduling marks requested automatic website creation as `pending_generation`, queues the CMS/article work, and carries article URL/status fields through the queue.
- Batch scheduling exposes pending website generation instead of reporting `not_configured` when automatic content generation is enabled.
- Schedule result banner reports per-Page failures and website-pending counts instead of generic success only.
- Immediate publish records persist website fields when an article URL was supplied.
- Mirrored source and packaged HTML templates remain identical.

## Verification

- Focused scheduling/embed tests: `26 passed`.
- Release guard + focused tests: `51 passed`.
- Full release gates during final build: `42 passed`, `25 passed`, `44 passed`, `3 passed`.
- Packaging guard: staged tree clean; no runtime state or machine identity.
- Production listener check: `127.0.0.1:5080` HTTP `200` before release work.

## Installer

- File: `release\Highlight_Desktop_Test_Setup_v1.0.19-preview.14.exe`
- Size: `683574784` bytes
- SHA256: `9da54e53712a1fccd5b043585dab26c45d800cc852278b59b447ea26ed3f4832`
- Expected tag: `v1.0.19-desktop-test.14`

## Release/deploy status

- Source commits are local and not yet pushed in this checkpoint.
- GitHub tag/release preview.14 was not present at the last check.
- Production was not overwritten by the installer build; existing persistent state remains outside the package.
