# Highlight Video Studio v1.0.19

Hotfix for installations that appeared unchanged after upgrading and for Page/token bindings that did not update the actual posting credential.

## Fixed

- Shows the active backend build clearly in the sidebar and top bar (`v1.0.19`).
- Serves HTML and API responses with no-cache headers so an old UI is not retained by the browser.
- Keeps build identity in application code because upgrades preserve the user's existing `config.json`.
- Detects when the image-generation URL was pasted into the model-list field and automatically resolves `/v1/images/generations` or `/v1/chat/completions` to `/v1/models`.
- Changes single-Page token assignment to use the Token Vault selector instead of treating raw text as a token ID.
- Updates `token_id`, `token_name`, and the actual Page posting token together for single and batch distribution.
- Rejects missing Token Vault IDs rather than reporting a false successful assignment.

## Verification

- 41 targeted regression tests pass.
- Live port 5080 reports `app_version: 1.0.19`.
- Live UI renders the v1.0.19 badge and no-cache headers.
- The reported image provider URL resolves to `/v1/models` and returns 20 models with the configured credential.
- Live token binding preserves the Vault ID and confirms the Page posting token and token name are populated.

The installer remains the Full Offline bundle and preserves user config, tokens, pages, schedules, jobs, downloads, output media, and browser profiles during overwrite installation.
