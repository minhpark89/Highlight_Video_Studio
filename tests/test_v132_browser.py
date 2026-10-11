import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from src import job_store


def test_jobs_filters_paging_and_polling_cannot_reset_manual_choice(tmp_path, monkeypatch):
    from web import app as api
    monkeypatch.setattr(api, "IS_QUEUE_PAUSED", True)
    monkeypatch.setattr(api, "JOBS_FILE", tmp_path / "jobs.json")
    monkeypatch.setattr(api, "RENDER_QUEUE_STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(api, "AUTO_CONCURRENT_JOBS", 2)
    monkeypatch.setattr(api, "MAX_CONCURRENT_JOBS", 2)
    monkeypatch.setattr(api, "CONCURRENCY_MODE", "auto")
    rows = [{"id":"job_" + str(i), "status":["error","queued","running","completed"][i % 4],
             "video_title":"Source " + str(i), "created_at":"2026-10-11",
             "error":"FFmpeg failed safely" if i % 4 == 0 else "", "clips":[]} for i in range(1264)]
    job_store.save(api.JOBS_FILE, rows)
    client = api.app.test_client()
    requests, errors = [], []
    root = Path(__file__).resolve().parents[1]
    evidence = root / "checkpoints" / "evidence" / "v1.3.2"
    evidence.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel="chrome")
        page = browser.new_page(viewport={"width":1400, "height":1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        def route_handler(route):
            request = route.request
            url = urlsplit(request.url)
            target = url.path + ("?" + url.query if url.query else "")
            if url.hostname != "highlight.test":
                route.abort()
                return
            requests.append(target)
            if url.path.startswith("/api/") and not url.path.startswith(("/api/jobs", "/api/queue")):
                route.fulfill(json={"success":True, "hardware":{}, "config":{}, "items":[],
                                    "posts":[], "groups":[], "pages":[], "tokens":[], "job_counts":{},
                                    "daily_posts":[], "recent_events":[], "youtube_logged_in":False})
                return
            result = client.open(target, method=request.method, data=request.post_data,
                                 content_type=request.headers.get("content-type"))
            route.fulfill(status=result.status_code, body=result.data,
                          content_type=result.content_type)
        page.route("**/*", route_handler)
        page.goto("http://highlight.test/", wait_until="domcontentloaded")
        page.wait_for_function("window.highlightRenderQueue && !window.highlightRenderQueue.request")
        assert not any(path.startswith(("/api/jobs", "/api/clips")) for path in requests)
        assert page.locator('link[rel="icon"]').get_attribute("href").startswith("/favicon.ico")
        page.locator('.nav-btn[data-pane="pane-jobs"]').click()
        page.wait_for_function("highlightJobs.request === null && document.querySelector('#jobs-table-body').children.length === 25")
        page.locator("#jobs-status-filter").select_option("error")
        page.wait_for_function("highlightJobs.request === null && document.querySelector('#jobs-counts').textContent.includes('Lỗi: 316')")
        assert page.locator("#jobs-table-body tr").count() == 25
        assert page.locator("#jobs-table-body").inner_text().count("ERROR") == 25
        assert "FFmpeg failed safely" in page.locator("#jobs-table-body").inner_text()
        page.locator("#jobs-next").click()
        page.wait_for_function("highlightJobs.request === null && highlightJobs.page === 2")
        page.locator("#jobs-search").fill("Source 1200")
        page.wait_for_function("highlightJobs.request === null && document.querySelector('#jobs-table-body').children.length === 1")
        assert "Source 1200" in page.locator("#jobs-table-body").inner_text()
        page.screenshot(path=str(evidence / "jobs-filter.png"))
        page.locator('.nav-btn[data-pane="pane-studio"]').click()
        page.locator("#queue-concurrency-mode").select_option("manual")
        page.locator("#queue-concurrency-manual").fill("4")
        page.evaluate("highlightRenderQueue.refresh()")
        assert page.locator("#queue-concurrency-mode").input_value() == "manual"
        assert page.locator("#queue-concurrency-manual").input_value() == "4"
        page.locator("#queue-concurrency-save").click()
        page.wait_for_function("!highlightRenderQueue.saving && !highlightRenderQueue.dirty")
        assert json.loads(api.RENDER_QUEUE_STATE_FILE.read_text())["manual_concurrency"] == 4
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("window.highlightRenderQueue && !highlightRenderQueue.request")
        assert page.locator("#queue-concurrency-mode").input_value() == "manual"
        assert page.locator("#queue-concurrency-manual").input_value() == "4"
        assert not errors, errors
        browser.close()
    (evidence / "offline_ui.json").write_text(json.dumps({
        "success":True, "checks":["1264 jobs with 25 visible rows", "error filter and counters",
            "pagination and search", "error message visible", "polling preserves unsaved manual 4",
            "manual 4 survives page reload", "favicon link", "no eager Jobs or gallery request"],
        "page_errors":errors, "scope":"actual frontend with isolated Flask APIs"}, indent=2), encoding="utf-8")
