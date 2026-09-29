# Highlight Video Studio preview.15 checkpoint — 2026-09-29

## Fixes in preview.15
- Meta preflight accepts `PROFILE_PLUS_MANAGE` as a publishing capability and still rejects read-only task sets.
- Content queue persists and returns website article URL and embed/video metadata; UI shows ready/pending/unconfirmed embed state.
- Source and packaged HTML templates match exactly.

## Verification
- Focused scheduling/embed/page-sync tests: 71 passed.
- Release groups: 42, 25, 44, and 27 passed.
- Packaging guard: clean staged payload, no runtime state or machine identity.
- Changed Python modules compile. Production listener `127.0.0.1:5080` returned HTTP 200.

## Installer
- `release\Highlight_Desktop_Test_Setup_v1.0.19-preview.15.exe`
- Size: 702410752 bytes
- SHA256: `be52839fd9ce7eb73b2762b412a3f5489bd9b2747bdecc5089fb7d995795cab5`
- Intended tag: `v1.0.19-desktop-test.15`

## Deployment
Build and verification are complete. GitHub release publication remains pending.
