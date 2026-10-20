import json
from pathlib import Path
import threading
from urllib.parse import urlsplit

from flask import Flask, render_template_string
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def test_all_navigation_and_unknown_publish_controls_over_http(tmp_path):
    root = Path(__file__).resolve().parents[1]
    server_app = Flask("navigation-test", static_folder=str(root / "web/static"))
    @server_app.get("/")
    def index():
        return render_template_string((root / "web/templates/index.html").read_text(encoding="utf-8"), app_version="1.3.4")
    server = make_server("127.0.0.1", 0, server_app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    errors = []
    requests = []
    evidence = root / "checkpoints/evidence/v1.3.4"
    evidence.mkdir(parents=True, exist_ok=True)
    resolved = False
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1080})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            def api(route):
                nonlocal resolved
                path = urlsplit(route.request.url).path
                payload = {"success": True, "config": {}, "hardware": {}, "groups": [], "tokens": [],
                           "pages": [], "posts": [], "items": [], "jobs": [], "clips": [], "profiles": [],
                           "counts": {}, "statistics": {}, "job_counts": {}, "daily_posts": [],
                           "recent_events": [], "pipeline": {"alive": True}, "stock": 0,
                           "page": 1, "total": 0, "completed": 0, "running": 0, "queued": 0}
                if path == "/api/posts/list":
                    payload["pages"] = 1
                elif path == "/api/scheduler/status":
                    payload.update(thread_alive=True, maintenance_thread_alive=True, last_cycle_ok=True,
                                   overdue_posts=[{"status": "scheduled", "id": "blocked", "blocked_reason": "Cần xác minh Token", "action": "tokens"}],
                                   blocked_count=1, actionable_count=0,
                                   meta_queue={"pending": 18, "overdue_meta": 18, "unknown_without_id": 5})
                elif path.endswith("/meta-diagnosis"):
                    payload.update(post_id="broken", title="Interrupted publish", page_name="Fixture Page", page_id="9901",
                                   post_status="draft" if resolved else "failed", observation={},
                                   diagnosis={"needs_operator_resolution": not resolved, "message": "Đối soát lần đăng bị gián đoạn"})
                elif path.endswith("/resolve-unknown"):
                    requests.append(route.request.post_data_json)
                    resolved = True
                    payload.update(status="draft", message="Đã chuyển về Draft sau đối soát.")
                route.fulfill(json=payload)
            page.route("**/api/**", api)
            page.route("**/favicon.ico**", lambda route: route.fulfill(status=204))
            page.goto(f"http://127.0.0.1:{server.server_port}/", wait_until="networkidle")
            page.locator('.nav-btn[data-pane="pane-posts"]').click()
            page.screenshot(path=str(evidence / "navigation-t0.png"))
            page.get_by_role("button", name="Chuẩn bị / Draft theo nhóm", exact=True).click()
            assert page.locator("#pane-groups").is_visible()
            assert page.locator(".pane:visible").count() == 1
            page.screenshot(path=str(evidence / "navigation-t1.png"))
            page.locator('.nav-btn[data-pane="pane-posts"]').click()
            page.get_by_role("button", name="Mở Token", exact=True).first.click()
            assert page.locator("#pane-tokens").is_visible()
            page.locator('.nav-btn[data-pane="pane-dashboard"]').click()
            page.locator('button.dashboard-stat[onclick="switchTab(\'pane-tokens\')"]').click()
            assert page.locator("#pane-tokens").is_visible()
            for pane in page.locator('.nav-btn[data-pane]').evaluate_all("nodes => nodes.map(node => node.dataset.pane)"):
                page.locator(f'.nav-btn[data-pane="{pane}"]').click()
                assert page.locator(f"#{pane}").is_visible(), pane
                assert page.locator(".pane:visible").count() == 1
            page.evaluate("switchTab('pane-does-not-exist')")
            assert page.locator(".pane:visible").count() == 1
            page.evaluate("openMetaDiagnosis('broken')")
            page.locator("#unknown-video-id").wait_for()
            retry = page.get_by_role("button", name="Chuyển về Draft sau đối soát", exact=True)
            assert retry.is_disabled()
            page.screenshot(path=str(evidence / "unknown-publish-recovery.png"))
            page.locator('[data-confirm-absent]').check()
            retry.click()
            page.wait_for_function("!document.querySelector('[data-confirm-absent]')")
            assert requests == [{"action": "return_to_draft", "confirmed_absent": True}]
            page.get_by_role("button", name="Mở Quản lý Token", exact=True).click()
            assert page.locator("#pane-tokens").is_visible()
            assert not page.locator("#modal-meta-diagnosis").is_visible()
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
    (evidence / "navigation-browser.json").write_text(json.dumps({
        "success": True, "errors": errors, "real_http_server": True,
        "checks": ["Draft shortcut", "Token warning shortcut", "Dashboard shortcut", "all sidebar tabs",
                   "invalid destination preserves visible pane", "unknown recovery confirmation", "dialog Token navigation"],
    }, indent=2), encoding="utf-8")
