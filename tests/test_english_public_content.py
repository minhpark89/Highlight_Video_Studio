import copy
import json
from unittest import mock

import pytest

from src.english_text import assert_english, assert_english_package
from src import content_packages as packages
from src.publisher.meta_reel_poster import MetaReelPoster
from core.website_article_service import WebsiteArticleService, WebsiteServiceError


@pytest.mark.parametrize("foreign", [
    "この動画では新しいゲームの詳細を紹介しています。",
    "这个视频介绍了游戏更新后的详细内容。",
    "이 영상에서는 게임 업데이트의 자세한 내용을 소개합니다.",
    "Это видео показывает подробности нового обновления игры.",
    "يعرض هذا الفيديو تفاصيل التحديث الجديد للعبة.",
    "Este video muestra todos los detalles de la nueva actualización del juego.",
    "Cette vidéo présente tous les détails de la nouvelle mise à jour du jeu.",
    "Video này giới thiệu chi tiết về bản cập nhật mới của trò chơi.",
])
def test_foreign_provider_output_is_rejected(foreign):
    with pytest.raises(ValueError):
        assert_english(foreign)


def test_html_paragraph_and_metadata_cannot_hide_inside_english_article():
    english = "<p>Watch the original recording for the full sequence and its context.</p>" * 20
    for addition in ("<p>Cette vidéo présente les détails de la nouvelle mise à jour.</p>",
                     '<img src="https://example.test/image" alt="元の動画">',
                     '<iframe src="https://example.test/video" title="原始视频"></iframe>'):
        with pytest.raises(ValueError):
            assert_english(english + addition)
    assert_english('<p>Specific video detail</p><a href="https://example.test/日本語">Read the story</a>')


def test_foreign_inputs_produce_english_fallback_without_copying_source(tmp_path, monkeypatch):
    monkeypatch.setattr(packages, "DATA_ROOT", tmp_path)
    result = packages.generate_package("超リアルなゲーム", "これは元の説明です。", mode="no_llm",
                                       article_url="https://example.test/story")
    assert_english_package(result)
    assert result["language"] == "en"
    assert "Original Video" in result["hero_title"]
    assert result["first_comment"].count("https://example.test/story") == 1


def test_component_retry_prompt_requires_english_and_retries_foreign_reply(tmp_path, monkeypatch):
    monkeypatch.setattr(packages, "CIRCUIT_FILE", tmp_path / "circuit.json")
    response = mock.Mock(status_code=200, headers={}, text="fixture")
    response.json.return_value = {"choices": [{"message": {"content": json.dumps({"caption": "这是原始视频的精彩片段。"})}}]}
    config = {"configured_base": "https://provider.test", "model": "fixture", "api_key": "fixture"}
    with mock.patch("src.content_builder.get_llm_candidates", return_value=config), \
         mock.patch("src.content_builder._get_task_model", return_value="fixture"), \
         mock.patch.object(packages.requests, "post", return_value=response) as post:
        with pytest.raises(ValueError):
            packages._llm_package("外国語", "source", component="caption")
    assert post.call_count == 2
    assert "English only" in post.call_args_list[0].kwargs["json"]["messages"][0]["content"]


def test_foreign_cached_package_cannot_bless_existing_cms_url():
    item = {"status": "ready", "article_url": "https://example.test/story", "website_status": "ready",
            "result": {"caption": "外国語の記事", "first_comment": "https://example.test/story"}}
    assert not packages._reusable(item, needs_article=True)
    url, state, error = packages.resolve_article_url(item)
    assert url == item["article_url"] and state == "failed"
    assert "same URL" in error


def test_large_queue_listing_does_not_reclassify_article_paragraphs():
    result = {"caption": "Watch the full original recording for complete context.",
              "article_html": "<p>Review the source recording to see the complete sequence.</p>" * 100}
    from src import english_text
    with mock.patch.object(english_text, "_factory", wraps=english_text._factory) as detector:
        for _ in range(100):
            assert not packages.package_needs_attention({"status": "ready", "result": result})
    assert detector.call_count <= 1
    # Deep validation at a write boundary still rejects a foreign paragraph.
    result["article_html"] += "<p>Cette vidéo présente tous les détails de la nouvelle mise à jour du jeu.</p>"
    with pytest.raises(ValueError):
        assert_english_package(result)


def test_all_meta_write_boundaries_reject_foreign_text_before_network(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fixture")
    with mock.patch("src.publisher.meta_reel_poster.requests.post") as write:
        poster = MetaReelPoster()
        assert not poster.publish_reel("9901", "fixture", video, description="外国語の記事")["success"]
        assert not poster.finish_existing_reel("9901", "fixture", "9001", "外国語の記事")["accepted"]
        assert not poster.post_first_comment("9001", "fixture", "外国語の記事")["success"]
    write.assert_not_called()


def test_cms_publish_rejects_foreign_raw_title_before_login():
    service = WebsiteArticleService.__new__(WebsiteArticleService)
    with mock.patch("core.website_article_service._BackendSession") as session:
        with pytest.raises(ValueError):
            service.publish_article("外国語の記事", "same-slug", "<p>Watch the full recording.</p>")
    session.assert_not_called()


def article_fixture():
    return {"id": 42, "slug": "same-slug", "version": "7", "title": "Old title",
            "description": '<p>Original text.</p><img src="https://img.test/one"><iframe src="https://video.test/one"></iframe>',
            "image": "https://img.test/one", "is_active": True, "is_home": False, "is_top": False,
            "categories": [{"id": 2}], "tags": [{"id": 3}]}


def repair_service():
    service = WebsiteArticleService.__new__(WebsiteArticleService)
    service.cfg = mock.Mock(api_base_url="https://cms.test/admin/api/v1", timeout=3)
    service._ensure_session = mock.Mock()
    service.verify_article = mock.Mock()
    return service


@pytest.mark.parametrize("changed", [{"version": "8"}, {"id": 99}, {"slug": "different"}, {"description": "New edit"}])
def test_cms_repair_stops_on_concurrent_edit_or_identity_change(changed):
    service = repair_service()
    old = article_fixture()
    service.read_existing_article = mock.Mock(return_value={**old, **changed})
    session = mock.Mock()
    with pytest.raises(WebsiteServiceError):
        service.update_existing_article("https://cms.test/blog/same-slug", title="New title",
                                        body_html=old["description"], expected_article=old, _session=session)
    session.http.put.assert_not_called()


def test_cms_repair_preserves_media_url_and_puts_same_id_once():
    service = repair_service()
    old = article_fixture()
    service.read_existing_article = mock.Mock(return_value=copy.deepcopy(old))
    session = mock.Mock()
    response = session.http.put.return_value
    response.status_code = 200
    response.json.return_value = {"ok": True, "data": {"id": 42}}
    repaired = old["description"].replace("Original text.", "Read the original recording for full context.")
    service.update_existing_article("https://cms.test/blog/same-slug", title="English title",
                                    body_html=repaired, expected_article=old, _session=session)
    session.http.put.assert_called_once()
    assert session.http.put.call_args.args[0].endswith("/posts/42")
    payload = session.http.put.call_args.kwargs["json"]
    assert payload["slug"] == old["slug"] and payload["version"] == "7"
    assert payload["image"] == old["image"] and payload["is_home"] is False
    assert payload["category_ids"] == [2] and payload["tag_ids"] == [3]
    session.http.post.assert_not_called()
    session.reset_mock()
    with pytest.raises(WebsiteServiceError):
        service.update_existing_article("https://cms.test/blog/same-slug", title="English title",
                                        body_html=repaired.replace("https://img.test/one", "https://img.test/two"),
                                        expected_article=old, _session=session)
    session.http.put.assert_not_called()


def test_cms_repair_can_add_missing_images_but_never_remove_existing_media():
    service = repair_service()
    old = article_fixture()
    service.read_existing_article = mock.Mock(return_value=copy.deepcopy(old))
    session = mock.Mock()
    session.http.put.return_value.json.return_value = {"ok": True}
    session.http.put.return_value.status_code = 200
    body = '<img src="https://img.test/new-hero">' + old["description"]
    service.update_existing_article("https://cms.test/blog/same-slug", title="English title", body_html=body,
        expected_article=old, allow_added_images=True, image_url="https://img.test/new-hero", _session=session)
    payload = session.http.put.call_args.kwargs["json"]
    assert payload["image"] == payload["og_image"] == "https://img.test/new-hero"
    session.reset_mock()
    with pytest.raises(WebsiteServiceError):
        service.update_existing_article("https://cms.test/blog/same-slug", title="English title",
            body_html=body.replace('<img src="https://img.test/one">', ''), expected_article=old,
            allow_added_images=True, _session=session)
    session.http.put.assert_not_called()
