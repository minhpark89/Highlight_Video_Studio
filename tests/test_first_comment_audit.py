import copy
from unittest import mock

import pytest

from src import content_packages as packages
from src.first_comment_profiles import load_profile_store


def web_module():
    # API checks must not start a render/publish worker during module import.
    with mock.patch("threading.Thread.start"):
        from web import app
    return app


def test_generate_route_passes_article_url_and_rejects_invalid_url():
    web = web_module()
    with mock.patch.object(web, "generate_package", return_value={"first_comment": "Read https://example.test/story"}) as generate:
        client = web.app.test_client()
        response = client.post("/api/content-studio/generate", json={
            "title": "Fixture", "article_url": "https://example.test/story", "first_comment_profile_id": "builtin_police",
        })
        assert response.status_code == 200
        assert generate.call_args.kwargs["article_url"] == "https://example.test/story"
        assert generate.call_args.kwargs["profile_id"] == "builtin_police"
        generate.reset_mock()
        for invalid in ("javascript:alert(1)", "https://user:password@example.test/story", "not-a-url"):
            response = client.post("/api/content-studio/generate", json={"title": "Fixture", "article_url": invalid})
            assert response.status_code == 400
        generate.assert_not_called()


@pytest.mark.parametrize("mode,model,expected_source", [("auto", "active-model", "llm"), ("no_llm", "", "template_fallback")])
def test_comment_component_retains_model_profile_and_origin(tmp_path, mode, model, expected_source):
    store = load_profile_store(tmp_path / "profiles.json")
    with mock.patch.object(packages, "circuit_status", return_value={"open": False}), mock.patch.object(
        packages, "_llm_package", return_value={"first_comment": "Read https://example.test/story", "source": "llm", "llm_model": model}
    ):
        result = packages.generate_package("Fixture", mode=mode, article_url="https://example.test/story",
                                           component="first_comment", profile_id="builtin_police", profile_store=store)
    assert result["first_comment"].count("https://example.test/story") == 1
    assert result["first_comment_source"] == expected_source
    assert result["first_comment_profile_id"] == "builtin_police"
    assert result["first_comment_profile_name"] == "Police"
    assert result["first_comment_model"] == model
    if mode == "no_llm":
        assert result["first_comment_fallback_reason"]


def test_comment_component_keeps_provider_failure_reason(tmp_path):
    with mock.patch.object(packages, "circuit_status", return_value={"open": False}), mock.patch.object(
        packages, "_llm_package", side_effect=RuntimeError("Configured model retired")
    ):
        result = packages.generate_package("Fixture", article_url="https://example.test/story", component="first_comment")
    assert result["first_comment_source"] == "template_fallback"
    assert result["first_comment_fallback_reason"] == "Configured model retired"


def test_existing_article_without_comment_tries_llm_before_template():
    item = {"title": "Fixture", "mode": "auto", "article_url": "https://example.test/story", "components": ["first_comment"],
            "first_comment_profile_id": "builtin_police", "result": {"caption": "Saved caption", "article_html": "Saved article", "source": "llm"}}
    with mock.patch.object(packages, "resolve_article_url", return_value=(item["article_url"], "ready", "")), mock.patch.object(
        packages, "generate_package", return_value={"first_comment": "LLM comment https://example.test/story",
            "source": "llm", "first_comment_source": "llm", "first_comment_model": "working", "first_comment_profile_id": "builtin_police"}
    ) as generate:
        packages._process_new_content_package(item)
    generate.assert_called_once()
    assert generate.call_args.kwargs["component"] == "first_comment"
    assert item["result"]["caption"] == "Saved caption"
    assert item["result"]["first_comment_source"] == "llm"
    assert item["result"]["first_comment_model"] == "working"


def test_reused_package_never_changes_posted_comment_status_snapshot_or_origin():
    web = web_module()
    post = {"status": "published", "first_comment_status": "posted", "first_comment": "Original comment",
            "first_comment_snapshot": "Original comment", "first_comment_source": "manual", "first_comment_profile_id": "original"}
    original = copy.deepcopy(post)
    web.apply_ready_package_to_post(post, {"first_comment_profile_id": "replacement", "result": {
        "first_comment": "Replacement comment", "first_comment_source": "llm", "first_comment_model": "new-model"}})
    for key in ("first_comment_status", "first_comment", "first_comment_snapshot", "first_comment_source", "first_comment_profile_id"):
        assert post[key] == original[key]


def test_reused_package_transfers_comment_metadata_when_creating_snapshot():
    web = web_module()
    post = {"status": "scheduled", "first_comment_status": "pending_generation", "first_comment": ""}
    web.apply_ready_package_to_post(post, {"first_comment_profile_id": "builtin_police", "result": {
        "first_comment": "Saved comment", "first_comment_source": "llm", "first_comment_model": "working",
        "first_comment_profile_name": "Police"}})
    assert post["first_comment_status"] == "ready"
    assert post["first_comment_model"] == "working"
    assert post["first_comment_profile_name"] == "Police"
    assert post["first_comment_snapshot"] == "Saved comment"


def test_package_failure_does_not_relabel_an_already_posted_comment(tmp_path):
    from web.posts_store import save_posts_file, load_posts_file
    path = tmp_path / "posts.json"
    save_posts_file(path, [{"id": "post", "status": "published", "first_comment_status": "posted", "first_comment_source": "llm"}])
    with mock.patch.object(packages, "DATA_ROOT", tmp_path):
        packages._apply_failure_to_posts({"post_ids": ["post"], "status": "failed", "error": "CMS failure"})
    post = load_posts_file(path)[0]
    assert post["first_comment_status"] == "posted" and post["first_comment_source"] == "llm"


def test_comment_retry_updates_origin_metadata_but_preserves_caption(tmp_path):
    path = tmp_path / "packages.json"
    packages._write(path, [{"id": "fixture", "title": "Fixture", "website_status": "ready",
        "article_url": "https://example.test/story", "result": {"caption": "Original", "source": "llm",
            "first_comment_source": "template_fallback", "first_comment_fallback_reason": "Old error"}}])
    with mock.patch.object(packages, "QUEUE_FILE", path), mock.patch.object(packages, "_apply_to_posts"), mock.patch.object(
        packages, "generate_package", return_value={"first_comment": "Read https://example.test/story", "source": "llm",
            "first_comment_source": "llm", "first_comment_model": "active", "first_comment_profile_name": "Police"}
    ):
        result = packages.retry_package_component("fixture", "first_comment")["package"]
    assert result["caption"] == "Original"
    assert result["first_comment_source"] == "llm"
    assert result["first_comment_model"] == "active"
    assert result["first_comment_fallback_reason"] == ""


def test_existing_article_enqueue_does_not_create_duplicate():
    web = web_module()
    with mock.patch.object(web, "enqueue_content_package", return_value={"id": "fixture"}) as enqueue, mock.patch.object(
        web, "start_content_package_worker"
    ):
        response = web.app.test_client().post("/api/content-studio/enqueue", json={
            "title": "Fixture", "article_url": "https://example.test/story", "create_website_article": True})
    assert response.status_code == 200
    assert enqueue.call_args.kwargs["article_url"] == "https://example.test/story"
    assert enqueue.call_args.kwargs["create_website_article"] is False


def test_queue_pause_survives_restart_until_explicit_resume(tmp_path):
    web = web_module()
    with mock.patch.object(web, "RENDER_QUEUE_STATE_FILE", tmp_path / "pause.json"), mock.patch.object(web, "IS_QUEUE_PAUSED", False):
        client = web.app.test_client()
        assert client.post("/api/queue/pause").status_code == 200
        assert web.load_render_queue_pause() is True
        assert client.post("/api/queue/resume").status_code == 200
        assert web.load_render_queue_pause() is False


def test_queue_does_not_report_cms_failure_as_llm_failure():
    web = web_module()
    with mock.patch.object(web, "list_packages", return_value=[{
        "id": "fixture", "status": "failed", "website_status": "failed", "website_error": "Source images missing",
        "result": {}, "mode": "auto"}]), mock.patch.object(web, "circuit_status", return_value={"open": False}):
        result = web.app.test_client().get("/api/content-studio/queue").get_json()
    assert result["items"][0]["llm_status"] == "blocked_website"
    assert result["llm_counts"]["failed"] == 0 and result["llm_counts"]["blocked_website"] == 1
