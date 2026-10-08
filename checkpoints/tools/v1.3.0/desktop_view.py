"""Inspect the installed UI without allowing browser write requests."""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

source = Path(__file__).resolve().parents[3]
root = source.parent
url = (root / "Highlight destop test/run/desktop_url.txt").read_text().strip()
local = root / "support/v1.3.0"
local.mkdir(parents=True, exist_ok=True)
report = {"success": False, "errors": [], "blocked_write_requests": [], "checks": []}
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, channel="msedge")
    page = browser.new_page(viewport={"width": 1600, "height": 1050})

    def guard(route):
        if route.request.method not in {"GET", "HEAD", "OPTIONS"}:
            report["blocked_write_requests"].append(route.request.url.split("?")[0].replace(url, ""))
            route.abort()
        else:
            route.continue_()

    page.route("**/*", guard)
    page.on("pageerror", lambda error: report["errors"].append(str(error)))
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_function("typeof loadPostsTable === 'function'")
    page.locator('.nav-btn[data-pane="pane-posts"]').click()
    page.wait_for_function("postsTableRequest === null && postsSnapshot.length > 0", timeout=30000)
    page.screenshot(path=str(local / "installed-posts.png"))
    report["checks"].append("Installed posts pane renders rows and completes loading")
    assert page.locator("#meta-recovery-mode").count() == 1
    assert page.locator("#meta-recovery-schedule").count() == 1
    report["checks"].append("Immediate and scheduled recovery controls exist in the installed DOM")
    assert not report["errors"], report["errors"]
    report["success"] = True
    browser.close()
(source / "checkpoints/evidence/v1.3.0/desktop_view.json").write_text(
    json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report))
