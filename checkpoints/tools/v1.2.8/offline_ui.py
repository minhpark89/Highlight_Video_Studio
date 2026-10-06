"""Exercise the recovery picker in Chromium with every request intercepted."""
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "checkpoints/evidence/v1.2.8"
EVIDENCE.mkdir(parents=True, exist_ok=True)
report = {"success": False, "checks": [], "errors": [], "requests": [], "live_http": False}
good = {"filename": "good.mp4", "title": "A verified original recording", "duration": 55.1, "size": 12000000,
        "width": 1080, "height": 1920, "valid": True, "source_url": "https://youtu.be/2GdRyatht4E"}
rendered = {**good, "filename": "_recovery/recovered-fixture.mp4", "title": "Rendered original recording", "status": "ready", "message": "MP4 đã kiểm tra. Mốc cắt cũ vượt nguồn; đã chọn đoạn hợp lệ."}
polls = 0

def route(r):
    global polls
    path = urlparse(r.request.url).path
    query = parse_qs(urlparse(r.request.url).query)
    report["requests"].append({"path": path, "method": r.request.method})
    if path == "/":
        return r.fulfill(content_type="text/html", body='''<html><head><meta charset="utf-8"><style>
        body{background:#0f172a;color:#e2e8f0;font:14px Arial;margin:20px}button{background:#1e293b;color:#e2e8f0;padding:8px;border:1px solid #475569;border-radius:6px}a{color:#93c5fd}label{display:block;margin-top:12px}.form-control{padding:8px;background:#1e293b;color:white;border:1px solid #475569;width:98%;margin:8px 0}
        </style></head><body><div id="modal-meta-diagnosis" style="display:flex;max-width:740px;margin:auto"><div style="width:100%"><h2>Đăng lại MP4 · Chọn video thay thế</h2><div id="body"></div><button id="meta-replace-failed">Tạo lịch thay thế</button></div></div></body></html>''')
    if path.endswith("/recovery-videos"):
        offset = int(query.get("offset", [0])[0])
        rows = [good, {"filename": "bad.mp4", "title": "Broken clip", "valid": False, "reason": "MP4 hỏng, không có luồng video."},
                {**good, "filename": "held.mp4", "title": "Reserved recording", "valid": False, "reason": "Đã được giữ cho bài/Page khác."}] if not offset else [{**good, "filename": "next.mp4"}]
        return r.fulfill(json={"success": True, "candidates": rows, "total": 13, "offset": offset, "next_offset": 12 if not offset else None})
    if path.endswith("/render-recovery"):
        if r.request.method == "POST":
            assert r.request.post_data_json == {"confirm_render": True, "video_id": "9001"}
            return r.fulfill(json={"success": True, "task": {"status": "running", "message": "Đang render từ video gốc..."}})
        polls += 1
        return r.fulfill(json={"success": True, "task": rendered})
    if path.endswith("/recovery-preview"):
        return r.fulfill(content_type="video/mp4", body=(ROOT / "tests/fixtures/tiny-video.mp4").read_bytes())
    return r.abort()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="chrome")
    page = browser.new_page(viewport={"width": 920, "height": 1100})
    page.route("**/*", route)
    page.on("pageerror", lambda error: report["errors"].append(str(error)))
    page.on("dialog", lambda dialog: dialog.accept())
    page.goto("http://recovery.test/")
    page.add_script_tag(content='''let currentMetaDiagnosisPost='bad', currentMetaDiagnosis={diagnosis:{can_replace_failed_video:true,video_id:'9001'}};
    function escapeHtml(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}''')
    page.add_script_tag(content=(ROOT / "web/static/video_recovery.js").read_text(encoding="utf-8"))
    page.evaluate("mountRecoveryVideos(document.getElementById('body'),'bad')")
    assert page.locator('input[value="bad.mp4"]').is_disabled()
    assert page.locator('input[value="held.mp4"]').is_disabled()
    assert page.locator('#meta-replace-failed').is_disabled()
    report["checks"].append("Only verified, unreserved stock videos are selectable")
    page.locator('input[value="good.mp4"]').check()
    assert page.locator('#meta-replacement-file').input_value() == 'good.mp4'
    assert page.locator('#recovery-preview').is_visible() and page.locator('#meta-replace-failed').is_enabled()
    report["checks"].append("Selecting a candidate opens preview and enables replacement")
    page.locator('#recovery-next').click()
    page.locator('input[value="next.mp4"]').wait_for()
    page.locator('input[value="next.mp4"]').check()
    assert page.locator('#meta-replacement-file').input_value() == 'next.mp4'
    report["checks"].append("Paged inventory retains explicit selection")
    page.locator('#recovery-prev').click()
    page.locator('input[value="good.mp4"]').wait_for()
    page.locator('#recovery-render').click()
    page.locator('input[value="_recovery/recovered-fixture.mp4"]').wait_for(timeout=15000)
    assert polls >= 1
    assert page.locator('#meta-replacement-file').input_value() == 'next.mp4'
    report["checks"].append("Render polls progress and does not select or schedule by itself")
    page.locator('input[value="_recovery/recovered-fixture.mp4"]').check()
    assert page.locator('#meta-replacement-file').input_value() == rendered['filename']
    assert page.locator('#recovery-render-status').inner_text().find('Mốc cắt') >= 0
    report["checks"].append("A validated render can be previewed and selected, with adjusted bounds disclosed")
    page.screenshot(path=str(EVIDENCE / 'recovery_picker.png'), full_page=True)
    assert not report["errors"], report["errors"]
    report["success"] = True
    (EVIDENCE / 'recovery_browser_ui.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    browser.close()
print(json.dumps({"success": report["success"], "checks": report["checks"], "errors": report["errors"]}, ensure_ascii=False))
