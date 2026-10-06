import copy
import json
import re
from unittest import mock

import pytest

from src import content_packages as packages
from src.publisher import website_publisher as publisher
from core.website_article_service import WebsiteServiceError
from web.posts_store import save_posts_file, load_posts_file


URL = "https://example.test/blog/existing"
YOUTUBE_ID = "2GdRyatht4E"


def old_article():
    return {"id": 42, "slug": "existing", "version": "7", "title": "外国語の記事",
        "image": "https://img.test/hero.jpg", "description":
        '<p>この動画では新しいゲームの詳細を紹介しています。</p><img src="https://img.test/hero.jpg" alt="元の動画">'
        '<img src="https://img.test/one.jpg"><img src="https://img.test/two.jpg">'
        f'<iframe src="https://www.youtube-nocookie.com/embed/{YOUTUBE_ID}" title="原始视频"></iframe>'}


@pytest.fixture
def repair(tmp_path, monkeypatch):
    service = mock.Mock()
    service.read_existing_article.return_value = old_article()
    monkeypatch.setattr(publisher, "get_website_config", lambda: ({"base_url": "https://example.test"}, tmp_path / "config.json"))
    monkeypatch.setattr(publisher, "WebsiteArticleService", lambda _: service)
    monkeypatch.setattr(publisher, "get_clip_metadata", lambda _: {"video_title": "Official launch trailer", "youtube_url": f"https://youtu.be/{YOUTUBE_ID}"})
    monkeypatch.setattr(publisher, "_source_video_summary", lambda meta, title: "The original recording contains the official launch trailer.")
    return service


def test_repair_translates_in_place_preserves_all_media_and_never_creates_article(repair):
    generated = packages.generate_package("Official launch trailer", mode="no_llm", article_url=URL)
    factory = mock.Mock(return_value=generated)
    metadata = {"result": {"article_html": "外国語の記事"}, "repair_existing_article": True}
    article_url, hero = publisher.repair_existing_website_article(URL, "clip.mp4", content_factory=factory, asset_metadata=metadata)
    assert article_url == URL and hero == old_article()["image"]
    repair.update_existing_article.assert_called_once()
    call = repair.update_existing_article.call_args
    assert call.args[0] == URL and call.kwargs["expected_article"]["id"] == 42
    assert call.kwargs["expected_article"]["slug"] == "existing"
    body = call.kwargs["body_html"]
    for tag in ("img", "iframe", "video", "source"):
        pattern = fr'<{tag}\b[^>]*\bsrc=["\']([^"\']+)'
        assert re.findall(pattern, old_article()["description"], re.I) == re.findall(pattern, body, re.I)
    assert "原始视频" not in body and "元の動画" not in body
    assert body.index('hero.jpg') < body.index('Original video summary') < body.index('one.jpg') < body.index('two.jpg') < body.index('Full Uncut Footage') < body.index('<iframe')
    repair.publish_article.assert_not_called()
    repair.upload_video.assert_not_called()
    repair.verify_article_english.assert_called_once_with(URL)
    assert metadata["website_video_status"] == "youtube_embed_verified"
    assert metadata["video_url"] == f"https://www.youtube.com/watch?v={YOUTUBE_ID}"
    assert metadata["website_repair_verified_at"] and not metadata.get("repair_existing_article")
    assert metadata["result"]["first_comment"].count(URL) == 1


def test_failed_verification_keeps_url_and_failed_state_in_package(repair):
    repair.verify_article_english.side_effect = WebsiteServiceError("Public article still contains foreign text")
    item = {"id": "repair", "clip_filename": "clip.mp4", "title": "Official launch trailer", "mode": "no_llm",
            "article_url": URL, "result": {"article_html": "外国語の記事"}, "repair_existing_article": True}
    url, state, error = packages.resolve_article_url(item)
    assert url == URL and state == "failed" and "foreign text" in error
    assert item["repair_existing_article"]
    repair.publish_article.assert_not_called()


def test_repair_missing_images_adds_assets_and_keeps_old_image_and_player(repair, monkeypatch):
    article = old_article()
    article["description"] = article["description"].replace('<img src="https://img.test/one.jpg"><img src="https://img.test/two.jpg">', '')
    repair.read_existing_article.return_value = article
    monkeypatch.setattr(publisher, "extract_and_upload_article_assets", lambda *args, **kwargs:
        ("https://img.test/new-hero.jpg", ["https://img.test/body-one.jpg", "https://img.test/body-two.jpg"]))
    publisher.repair_existing_website_article(URL, "clip.mp4",
        content_factory=lambda url, source: packages.generate_package("Official launch trailer", mode="no_llm", article_url=url),
        asset_metadata={"regenerate_text": True})
    call = repair.update_existing_article.call_args.kwargs
    assert call["allow_added_images"] and call["image_url"] == "https://img.test/new-hero.jpg"
    assert "https://img.test/hero.jpg" in call["body_html"] and f"/embed/{YOUTUBE_ID}" in call["body_html"]
    repair.publish_article.assert_not_called()


def test_real_english_revalidation_does_not_rewrite_existing_article(repair):
    article = old_article()
    article['title'] = 'Bodycam: Unpacking the Hype, Visual Realism, and Gaming Implications'
    article['description'] = '<p>Even ideal weapon builds depend heavily on smart movement discipline and engagement distance management.</p>' * 45 + \
        f'<iframe src="https://www.youtube-nocookie.com/embed/{YOUTUBE_ID}" title="Original video"></iframe>'
    repair.read_existing_article.return_value = article
    generated = packages.generate_package('Official launch trailer', mode='no_llm', article_url=URL)
    publisher.repair_existing_website_article(URL, 'clip.mp4', content_factory=mock.Mock(return_value=generated),
                                              asset_metadata={'result': generated, 'repair_existing_article': True})
    repair.update_existing_article.assert_not_called()
    repair.publish_article.assert_not_called()
    repair.verify_article_english.assert_called_once_with(URL)


def test_mixed_foreign_paragraph_triggers_in_place_repair_even_if_overall_is_english(repair):
    article = old_article()
    article['title'] = 'Original video breakdown'
    article['description'] = '<p>Read the original recording for the complete sequence and its context.</p>' * 20 + \
        '<p>Cette vidéo présente les détails de la nouvelle mise à jour.</p>' + \
        f'<iframe src="https://www.youtube-nocookie.com/embed/{YOUTUBE_ID}" title="Original video"></iframe>'
    repair.read_existing_article.return_value = article
    generated = packages.generate_package('Official launch trailer', mode='no_llm', article_url=URL)
    publisher.repair_existing_website_article(URL, 'clip.mp4', content_factory=mock.Mock(return_value=generated),
                                              asset_metadata={'result': generated, 'repair_existing_article': True})
    repair.update_existing_article.assert_called_once()


def test_retry_worker_repairs_same_url_then_resumes_comment_and_schedule(tmp_path, monkeypatch, repair):
    monkeypatch.setattr(packages, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(packages, "QUEUE_FILE", tmp_path / "packages.json")
    item = packages.enqueue_content_package(clip_filename="clip.mp4", title="Official launch trailer",
        mode="no_llm", article_url=URL, post_ids=["post"], create_website_article=True)
    queued = packages._read(packages.QUEUE_FILE, [])
    queued[0].update(status="failed", website_status="failed", website_error="Existing CMS article contains non-English content",
                     result={"hero_title": "外国語の記事", "article_html": "外国語の記事"})
    packages._write(packages.QUEUE_FILE, queued)
    save_posts_file(tmp_path / "posts.json", [{"id": "post", "status": "failed", "retry_stage": "website_content",
        "retryable": True, "scheduled_time": "2099-01-01 12:00:00", "content_package_id": item["id"],
        "article_url": URL, "website_status": "failed", "first_comment_status": "generation_failed"}])
    assert packages.retry_package(item["id"])["repair_existing_article"]
    result = packages.process_content_packages_once()
    assert result["item"]["status"] == "ready", result["item"]
    post = load_posts_file(tmp_path / "posts.json")[0]
    assert post["status"] == "scheduled" and post["article_url"] == URL and post["website_status"] == "ready"
    assert post["website_embed_status"] == "ready" and post["website_video_status"] == "youtube_embed_verified"
    assert post["first_comment_status"] == "ready" and post["first_comment"].count(URL) == 1
    assert post["scheduled_time"] == "2099-01-01 12:00:00"
    assert not post["first_comment_error"] and not post["content_package_error"]
    repair.publish_article.assert_not_called()


def test_website_retry_endpoint_enqueues_repair_for_existing_url_without_meta(tmp_path, monkeypatch):
    from web import app as api
    monkeypatch.setattr(packages, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(packages, "QUEUE_FILE", tmp_path / "packages.json")
    path = tmp_path / "posts.json"
    save_posts_file(path, [{"id": "post", "status": "scheduled", "scheduled_time": "2099-01-01 12:00:00",
        "article_url": URL, "website_status": "failed", "title": "Official launch trailer", "media_file": "clip.mp4",
        "first_comment_status": "generation_failed", "token": "secret"}])
    monkeypatch.setattr(api, "POSTS_FILE", path)
    with mock.patch.object(api, "start_content_package_worker"), mock.patch.object(api.reel_poster, "publish_reel") as write:
        response = api.app.test_client().post("/api/posts/post/retry-website")
    assert response.status_code == 202 and response.get_json()["queued"]
    assert "secret" not in response.get_data(as_text=True)
    assert packages.list_packages()[0]["repair_existing_article"]
    post = load_posts_file(path)[0]
    assert post["article_url"] == URL and post["status"] == "scheduled"
    assert post["website_status"] == "pending_generation"
    write.assert_not_called()


def test_repair_updates_frozen_website_verification_without_changing_post_or_comment(tmp_path, monkeypatch):
    monkeypatch.setattr(packages, "DATA_ROOT", tmp_path)
    original = {"id": "post", "status": "published", "content_frozen_at": "approved", "title": "Approved title",
        "content": "Approved caption", "post_fb_id": "9001", "article_url": URL, "website_status": "failed",
        "first_comment_status": "posted", "first_comment_snapshot": "Approved " + URL, "comment_id": "comment"}
    save_posts_file(tmp_path / "posts.json", [original])
    result = packages.generate_package("New title", mode="no_llm", article_url=URL)
    with mock.patch("src.publisher.first_comment_queue.enqueue_first_comment") as comment:
        packages._apply_to_posts({"id": "package", "post_ids": ["post"], "result": result, "status": "ready",
            "article_url": URL, "website_status": "ready", "website_error": "", "embed_status": "ready",
            "website_video_status": "youtube_embed_verified", "website_repair_verified_at": "verified"})
    saved = load_posts_file(tmp_path / "posts.json")[0]
    assert saved["website_status"] == "ready" and saved["website_embed_status"] == "ready"
    for key in ("status", "title", "content", "post_fb_id", "first_comment_snapshot", "comment_id", "first_comment_status"):
        assert saved[key] == original[key]
    comment.assert_not_called()
