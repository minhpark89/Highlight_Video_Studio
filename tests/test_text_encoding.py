from pathlib import Path
from unittest import mock

from core.text_encoding import mojibake_marker_score, repair_mojibake, repair_mojibake_text


def test_repairs_known_vietnamese_mojibake_and_preserves_clean_text():
    corrupt = "Trá»‹nh Sát CÃ¡nh"
    clean = "Trịnh Sát Cánh"
    assert repair_mojibake_text(corrupt) == clean
    assert repair_mojibake_text(clean) == clean
    assert mojibake_marker_score(repair_mojibake_text(corrupt)) < mojibake_marker_score(corrupt)


def test_repairs_mixed_fields_recursively_without_changing_non_strings():
    value = {
        "title": "Cáº£nh Sát",
        "progress_msg": "Äang render clip",
        "clips": [{"hook_title": "Trá»‹nh Sát"}],
        "step": 4,
        "filename": "Cáº£nh Sát.mp4",
    }
    repaired = repair_mojibake(value)
    assert repaired["title"] == "Cảnh Sát"
    assert repaired["progress_msg"] == "Đang render clip"
    assert repaired["clips"][0]["hook_title"] == "Trịnh Sát"
    assert repaired["step"] == 4
    assert repaired["filename"] == value["filename"]


def test_does_not_force_unrelated_unicode_or_partial_text():
    clean = "Cảnh Sát — Đang render"
    assert repair_mojibake_text(clean) == clean
    assert repair_mojibake_text("ASCII title") == "ASCII title"
    assert repair_mojibake_text("Cảnh Sát Trá»‹nh") == "Cảnh Sát Trịnh"
    assert repair_mojibake_text("� lost byte") == "� lost byte"


def test_jobs_and_clip_api_repair_response_without_mutating_stored_records(tmp_path):
    import web.app as web_app

    bad = {
        "id": "fixture-job", "video_title": "Cáº£nh Sát", "progress_msg": "Äang render Trá»‹nh",
        "clips": [{"filename": "fixture.mp4", "hook_title": "Trá»‹nh Sát", "title": "Cáº£nh Sát"}],
    }
    good = {"id": "clean-job", "video_title": "Cảnh Sát", "clips": []}
    (tmp_path / "fixture.mp4").write_bytes(b"test")
    with mock.patch.object(web_app, "load_jobs", return_value=[bad, good]), mock.patch.object(
        web_app, "OUTPUT_DIR", tmp_path
    ), mock.patch.object(web_app, "BASE_DIR", tmp_path):
        client = web_app.app.test_client()
        jobs = client.get("/api/jobs").get_json()
        detail = client.get("/api/jobs/fixture-job").get_json()
        clips = client.get("/api/clips").get_json()
    assert jobs[0]["video_title"] == detail["video_title"] == "Cảnh Sát"
    assert detail["progress_msg"] == "Đang render Trịnh"
    assert jobs[1]["video_title"] == "Cảnh Sát"
    assert clips[0]["hook_title"] == "Trịnh Sát"
    assert clips[0]["title"] == "Cảnh Sát"
    assert bad["video_title"] == "Cáº£nh Sát"
    assert bad["clips"][0]["title"] == "Cáº£nh Sát"


def test_source_status_strings_are_utf8_and_not_mojibake():
    for relative in ("web/app.py", "src/pipeline.py"):
        source = Path(relative).read_text(encoding="utf-8")
        assert mojibake_marker_score(source) == 0
    app_source = Path("web/app.py").read_text(encoding="utf-8")
    pipeline_source = Path("src/pipeline.py").read_text(encoding="utf-8")
    assert "Đã tạm dừng nhận link mới từ hàng đợi." in app_source
    assert "Đang phân tích lời thoại và tạo phụ đề chạy chữ" in pipeline_source
    assert "Bạn là một chuyên gia biên tập video ngắn viral" in pipeline_source


def test_served_template_has_utf8_and_escapes_metadata_in_cards_and_modal():
    import web.app as web_app

    response = web_app.app.test_client().get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '<meta charset="utf-8">' in html
    assert "const title = escapeHtml(String(c.title || c.hook_title || c.filename || ''));" in html
    assert "${escapeHtml(String(j.progress_msg || 'Không có thông báo tiến độ mới.'))}" in html
    assert "${escapeHtml(String(j.error))}" in html
    assert Path("web/index.html").read_bytes() == Path("web/templates/index.html").read_bytes()
