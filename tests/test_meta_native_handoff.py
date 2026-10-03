import json
import time
from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest
import requests

from src.publisher.meta_reel_poster import MetaReelPoster


def meta_response(payload, status=200):
    response = mock.Mock(status_code=status, ok=status < 400, headers={}, text="fixture")
    response.json.return_value = payload
    return response


@pytest.mark.parametrize("finish", [requests.Timeout("fixture"), ValueError("fixture"), [], None])
def test_ambiguous_finish_preserves_upload_id_and_prevents_retry(tmp_path, finish):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")
    responses = [meta_response({"video_id": "9001"}), meta_response({"success": True})]
    if isinstance(finish, requests.Timeout):
        responses.append(finish)
    else:
        response = meta_response(finish)
        if isinstance(finish, ValueError):
            response.json.side_effect = finish
        responses.append(response)
    initialized = mock.Mock()
    with mock.patch("src.publisher.meta_reel_poster.requests.post", side_effect=responses), mock.patch(
        "src.publisher.meta_reel_poster.requests.get"
    ) as read:
        result = MetaReelPoster().publish_reel(
            "9901", "fixture-token", video, schedule_time=int(time.time()) + 900,
            on_upload_initialized=initialized,
        )
    assert result["processing"] and result["outcome_unknown"]
    assert result["meta_video_id"] == result["upload_video_id"] == "9001"
    initialized.assert_called_once_with("9001")
    read.assert_not_called()


@pytest.mark.parametrize("offset", [600, -1, 29 * 86400 + 60])
def test_invalid_schedule_is_rejected_before_any_graph_call(tmp_path, offset):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")
    with mock.patch("src.publisher.meta_reel_poster.requests.post") as write:
        result = MetaReelPoster().publish_reel(
            "9901", "fixture-token", video, schedule_time=int(time.time()) + offset,
        )
    assert not result["success"]
    write.assert_not_called()


def test_persistence_failure_stops_before_transfer_and_finish(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")
    with mock.patch("src.publisher.meta_reel_poster.requests.post", return_value=meta_response({"video_id": "9001"})) as write:
        result = MetaReelPoster().publish_reel(
            "9901", "fixture-token", video, schedule_time=int(time.time()) + 900,
            on_upload_initialized=mock.Mock(side_effect=OSError("fixture")),
        )
    assert write.call_count == 1
    assert result["outcome_unknown"] and result["meta_video_id"] == "9001"


def test_verified_schedule_queues_comment_with_exact_post_and_token(tmp_path):
    from src.publisher import first_comment_queue

    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")
    publish_at = int(time.time()) + 900
    responses = [meta_response({"video_id": "9001"}), meta_response({"success": True}), meta_response({"success": True})]
    status = {"id": "9001", "status": {"publishing_phase": {"publish_status": "scheduled", "publish_time": publish_at}}}
    with mock.patch("src.publisher.meta_reel_poster.requests.post", side_effect=responses) as write, mock.patch(
        "src.publisher.meta_reel_poster.requests.get", return_value=meta_response(status)
    ), mock.patch.object(first_comment_queue, "QUEUE_FILE", tmp_path / "comments.json"):
        result = MetaReelPoster().publish_reel(
            "9901", "fixture-token", video, schedule_time=publish_at,
            first_comment="Read https://example.test/story", token_id="tok_exact", post_id="post_exact",
        )
    assert result["success"] and result["status"] == "SCHEDULED"
    assert write.call_args.kwargs["data"]["video_state"] == "SCHEDULED"
    item = json.loads((tmp_path / "comments.json").read_text())[0]
    assert item["post_id"] == "post_exact" and item["token_id"] == "tok_exact"
    assert item["meta_video_id"] == "9001" and item["due_at"] == publish_at + 30


def test_schedule_mismatch_is_not_accepted_as_handoff():
    status = {"id": "9001", "status": {"publishing_phase": {"publish_status": "scheduled", "publish_time": 1800000000}}}
    with mock.patch("src.publisher.meta_reel_poster.requests.get", return_value=meta_response(status)):
        result = MetaReelPoster().check_scheduled_reel("9001", "fixture-token", 1800000900)
    assert not result["verified"] and result["status"] == "schedule_mismatch"


@pytest.fixture
def isolated_api(tmp_path, monkeypatch):
    from web import app as web_app
    from src.publisher.page_manager import PageManager
    from src.publisher.token_vault import TokenVault

    vault = TokenVault(tmp_path)
    pages = PageManager(tmp_path)
    credential = {"id": "tok_exact", "name": "Fixture", "token": "fixture-token", "status": "ACTIVE"}
    vault._save([credential])
    pages.sync_pages_from_token(credential, [{"id": "9901", "name": "Fixture Page", "access_token": "fixture-page-token", "tasks": ["CREATE_CONTENT"]}])
    output = tmp_path / "output"
    output.mkdir()
    (output / "clip.mp4").write_bytes(b"video")
    for name, value in {
        "BASE_DIR": tmp_path, "POSTS_FILE": tmp_path / "posts.json", "OUTPUT_DIR": output,
        "TOKEN_GROUPS_FILE": tmp_path / "token_groups.json",
        "FIRST_COMMENT_PROFILES_FILE": tmp_path / "profiles.json",
        "token_vault": vault, "page_manager": pages,
    }.items():
        monkeypatch.setattr(web_app, name, value)
    monkeypatch.setitem(web_app.app.config, "TESTING", True)
    return web_app, web_app.app.test_client(), vault, pages


def native_payload():
    return {"page_id": "9901", "filename": "clip.mp4", "title": "Fixture",
            "schedule_time": int(time.time()) + 900, "publish_mode": "meta_scheduled",
            "article_url": "https://example.test/story", "first_comment": "Read https://example.test/story"}


def test_native_api_persists_upload_id_before_finish_and_blocks_second_upload(isolated_api, tmp_path):
    web_app, client, vault, pages = isolated_api

    def uncertain_publish(**kwargs):
        kwargs["on_upload_initialized"]("9001")
        saved = json.loads((tmp_path / "posts.json").read_text())[0]
        assert saved["meta_video_id"] == "9001" and saved["status"] == "processing"
        return {"success": False, "outcome_unknown": True, "error": "fixture"}

    with mock.patch.object(web_app.reel_poster, "publish_reel", side_effect=uncertain_publish) as publish:
        response = client.post("/api/publish/reel", json=native_payload())
        second = client.post("/api/publish/reel", json=native_payload())
    saved = json.loads((tmp_path / "posts.json").read_text())[0]
    assert response.status_code == 200
    assert saved["status"] == "processing" and saved["meta_video_id"] == "9001"
    assert saved["outcome_unknown"] and not saved["retryable"]
    assert publish.call_count == 1
    assert second.get_json()["success_count"] == 0


def test_reconciliation_before_due_uses_original_token_and_recovers_comment_queue(tmp_path):
    from web import scheduled_publisher as worker
    from src.publisher import first_comment_queue
    from src.publisher.page_manager import PageManager
    from src.publisher.token_vault import TokenVault

    original = {"id": "tok_exact", "name": "Original", "token": "fixture-original", "status": "ACTIVE"}
    replacement = {"id": "tok_new", "name": "New", "token": "fixture-new", "status": "ACTIVE"}
    TokenVault(tmp_path)._save([original, replacement])
    manager = PageManager(tmp_path)
    manager.sync_pages_from_token(original, [{"id": "9901", "access_token": "page-original", "tasks": ["CREATE_CONTENT"]}])
    manager.sync_pages_from_token(replacement, [{"id": "9901", "access_token": "page-new", "tasks": ["CREATE_CONTENT"]}])
    pages = manager.list_pages()
    pages[0]["token_id"] = "tok_new"
    manager.save_pages(pages)
    publish_at = int(time.time()) + 900
    row = {"id": "post_exact", "status": "processing", "publish_mode": "meta_scheduled", "page_id": "9901",
           "token_id": "tok_exact", "meta_video_id": "9001", "meta_scheduled_publish_time": publish_at,
           "first_comment": "Read https://example.test/story", "first_comment_status": "waiting_meta"}
    posts_file = tmp_path / "posts.json"
    posts_file.write_text(json.dumps([row]))
    with mock.patch.object(worker, "BASE_DIR", tmp_path), mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
        first_comment_queue, "QUEUE_FILE", tmp_path / "comments.json"
    ), mock.patch.object(MetaReelPoster, "check_scheduled_reel", return_value={
        "verified": True, "status": "scheduled", "video_id": "9001", "publish_time": publish_at,
    }) as verify:
        worker._process_scheduled_posts_once(poster=mock.Mock(), now=datetime.now())
    assert verify.call_args.args[1] == "page-original"
    saved = json.loads(posts_file.read_text())[0]
    assert saved["status"] == "meta_scheduled" and saved["token_id"] == "tok_exact"
    queued = json.loads((tmp_path / "comments.json").read_text())[0]
    assert queued["token_id"] == "tok_exact" and queued["post_id"] == "post_exact"


def test_delete_refuses_token_needed_by_processing_post_even_without_page_binding(isolated_api, tmp_path):
    web_app, client, vault, pages = isolated_api
    pages.save_pages([])
    (tmp_path / "posts.json").write_text(json.dumps([{"id": "post_exact", "status": "processing", "token_id": "tok_exact"}]))
    response = client.delete("/api/tokens/tok_exact")
    assert response.status_code == 409
    assert vault.get_token_by_id("tok_exact") is not None


def test_missing_group_credential_rejects_schedule_before_upload(isolated_api, tmp_path):
    web_app, client, vault, pages = isolated_api
    web_app.save_token_groups([{"id": "pool", "name": "Fixture", "token_ids": ["tok_exact", "tok_missing"], "page_ids": ["9901"]}])
    with mock.patch.object(web_app.reel_poster, "publish_reel") as publish:
        response = client.post("/api/publish/reel", json={**native_payload(), "token_group_id": "pool"})
    assert response.status_code == 409
    publish.assert_not_called()


def test_profile_crud_default_and_regenerate_are_link_safe(isolated_api):
    from src.first_comment_profiles import builtin_profiles
    from src import content_builder

    web_app, client, vault, pages = isolated_api
    samples = [f"Read the verified source for context {index}." for index in range(30)]
    created = client.post("/api/first-comment-profiles", json={
        "name": "Custom Sports", "niche": "sports", "lead_ins": samples, "make_default": True,
    })
    assert created.status_code == 201
    profile_id = created.get_json()["profile"]["id"]
    listed = client.get("/api/first-comment-profiles").get_json()
    assert listed["default_profile_id"] == profile_id
    assert {profile["niche"] for profile in listed["profiles"]} == {"police", "sports", "news", "rescue", "reality", "general"}
    duplicate = client.post("/api/first-comment-profiles", json={"name": "custom sports", "niche": "sports", "lead_ins": samples})
    assert duplicate.status_code == 409
    invalid = client.put(f"/api/first-comment-profiles/{profile_id}", json={
        "name": "Custom Sports", "niche": "sports", "lead_ins": ["https://untrusted.test"] * 30,
    })
    assert invalid.status_code == 400
    response = meta_response({"choices": [{"message": {"content": json.dumps({"templates": samples})}}]})
    with mock.patch.object(content_builder, "get_llm_candidates", return_value={
        "configured_base": "https://llm.test/v1", "model": "fixture", "api_key": "fixture-key",
    }), mock.patch.object(content_builder, "_get_task_model", return_value="fixture"), mock.patch.object(
        web_app.requests, "post", return_value=response
    ) as generate:
        regenerated = client.post(f"/api/first-comment-profiles/{profile_id}/regenerate")
    assert regenerated.status_code == 200
    assert len(regenerated.get_json()["profile"]["lead_ins"]) == 30
    assert "niche=sports" in generate.call_args.kwargs["json"]["messages"][0]["content"]
    deleted = client.delete(f"/api/first-comment-profiles/{profile_id}")
    assert deleted.status_code == 200
    assert deleted.get_json()["default_profile_id"] != profile_id


def test_retry_first_comment_preserves_custom_profile_and_exact_url_once(tmp_path):
    from src import content_packages as packages
    from src.first_comment_profiles import save_profile_store

    profile_id = "custom_sports"
    store = {"default_profile_id": profile_id, "profiles": [{
        "id": profile_id, "name": "Sports", "niche": "sports",
        "lead_ins": [f"Review sports context number {index}." for index in range(30)],
    }]}
    save_profile_store(tmp_path / "data" / "first_comment_profiles.json", store)
    url = "https://example.test/story"
    queue = tmp_path / "packages.json"
    queue.write_text(json.dumps([{"id": "package", "title": "Fixture", "article_url": url,
                                "website_status": "ready", "first_comment_profile_id": profile_id}]))
    with mock.patch.object(packages, "DATA_ROOT", tmp_path), mock.patch.object(packages, "QUEUE_FILE", queue), mock.patch.object(
        packages, "generate_package", return_value={"first_comment": f"{url} {url}", "source": "llm"}
    ), mock.patch.object(packages, "_apply_to_posts"):
        result = packages.retry_package_component("package", "first_comment")
    assert result["item"]["first_comment_profile_id"] == profile_id
    assert result["package"]["first_comment"].count(url) == 1
    assert result["package"]["first_comment"].startswith("Review sports context")


def test_profile_updates_do_not_mutate_scheduled_comment_snapshot(tmp_path):
    from src import content_packages as packages

    posts_file = tmp_path / "posts.json"
    posts_file.write_text(json.dumps([{"id": "scheduled", "status": "scheduled", "first_comment": "Old snapshot",
                                      "first_comment_snapshot": "Old snapshot", "first_comment_profile_id": "old_profile",
                                      "first_comment_source": "manual"}]))
    with mock.patch.object(packages, "DATA_ROOT", tmp_path):
        packages._apply_to_posts({"id": "package", "post_ids": ["scheduled"], "status": "ready",
                                  "first_comment_profile_id": "new_profile", "result": {
                                      "first_comment": "New snapshot", "first_comment_source": "llm",
                                  }})
    saved = json.loads(posts_file.read_text())[0]
    assert saved["first_comment"] == saved["first_comment_snapshot"] == "Old snapshot"
    assert saved["first_comment_profile_id"] == "old_profile"
    assert saved["first_comment_source"] == "manual"


def test_ambiguous_comment_queue_is_not_retried(tmp_path):
    from src.publisher import first_comment_queue

    poster = mock.Mock()
    poster.post_first_comment.return_value = {"success": False, "outcome_unknown": True}
    with mock.patch.object(first_comment_queue, "QUEUE_FILE", tmp_path / "comments.json"):
        first_comment_queue.enqueue_first_comment("9001", "fixture", "Read the article", 1, post_id="post")
        first_comment_queue.process_due_first_comments(poster, now=2)
        first_comment_queue.process_due_first_comments(poster, now=999)
        first_comment_queue.enqueue_first_comment("9001", "fixture", "Read the article", 1000, post_id="post")
    rows = json.loads((tmp_path / "comments.json").read_text())
    assert len(rows) == 1 and rows[0]["status"] == "verification_pending"
    assert poster.post_first_comment.call_count == 1


def test_comment_is_deferred_until_independent_publication_verification(tmp_path):
    from src.publisher import first_comment_queue

    poster = mock.Mock()
    with mock.patch.object(first_comment_queue, "QUEUE_FILE", tmp_path / "comments.json"):
        first_comment_queue.enqueue_first_comment("9001", "fixture", "Read the article", 1, post_id="post")
        first_comment_queue.process_due_first_comments(poster, now=2, prepare=lambda item: {"ready": False})
    rows = json.loads((tmp_path / "comments.json").read_text())
    assert rows[0]["attempts"] == 0 and rows[0]["status"] == "pending"
    poster.post_first_comment.assert_not_called()


def test_enqueued_package_keeps_profile_templates_after_default_changes(tmp_path):
    from src import content_packages as packages
    from src.first_comment_profiles import save_profile_store

    profile_id = "custom"
    store = {"default_profile_id": profile_id, "profiles": [{"id": profile_id, "name": "Fixture", "niche": "sports",
             "lead_ins": [f"Review sports source context {index}." for index in range(30)]}]}
    save_profile_store(tmp_path / "data" / "first_comment_profiles.json", store)
    with mock.patch.object(packages, "DATA_ROOT", tmp_path), mock.patch.object(packages, "QUEUE_FILE", tmp_path / "packages.json"):
        item = packages.enqueue_content_package(clip_filename="clip.mp4", title="Fixture", first_comment_profile_id=profile_id)
        store["profiles"][0]["lead_ins"] = [f"Changed source context {index}." for index in range(30)]
        save_profile_store(tmp_path / "data" / "first_comment_profiles.json", store)
        result = packages.generate_package("Fixture", mode="no_llm", article_url="https://example.test/story",
                                           profile_id=profile_id, profile_store=item["first_comment_profile_store"])
    assert result["first_comment"].startswith("Review sports source context")
