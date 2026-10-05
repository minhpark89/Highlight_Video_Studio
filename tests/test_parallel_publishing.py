import json
import threading
from datetime import datetime
from unittest import mock

import pytest

from multi_pc.publishing_settings import load_publishing_settings, save_publishing_settings
from web.posts_store import load_posts_file, save_posts_file


@pytest.mark.parametrize("threads", [1, 2, 4, 8])
def test_parallel_workers_preserve_results_upload_ids_and_concurrent_metadata(tmp_path, threads):
    from web import scheduled_publisher as worker
    path = tmp_path / "posts.json"
    output = tmp_path / "output"
    output.mkdir()
    (output / "clip.mp4").write_bytes(b"fixture")
    count = min(threads, 4)
    rows = [{"id": f"p{i}", "page_id": f"page{i}", "token": f"fixture{i}",
             "status": "scheduled", "scheduled_time": "2026-10-01 10:00:00",
             "media_file": "clip.mp4"} for i in range(4)]
    save_posts_file(path, rows)
    save_publishing_settings(tmp_path, threads)
    barrier = threading.Barrier(count)

    class Poster:
        def publish_reel(self, **args):
            args["on_upload_initialized"]("upload-" + args["page_id"])
            barrier.wait(timeout=5)
            if args["page_id"] == "page0":
                revision = load_posts_file(path)
                revision[0]["content_package_source"] = "concurrent-fixture"
                revision.append({"id": "operator-new-row", "status": "scheduled"})
                save_posts_file(path, revision)
            return {"success": True, "video_id": "reel-" + args["page_id"]}

    with mock.patch.object(worker, "POSTS_FILE", path), mock.patch.object(worker, "OUTPUT_DIR", output), \
         mock.patch.object(worker, "POSTED_CLIPS_FILE", tmp_path / "posted.json"), \
         mock.patch("src.publisher.first_comment_queue.process_due_first_comments", return_value={}), \
         mock.patch("src.publisher.token_vault.TokenVault"), mock.patch("src.publisher.page_manager.PageManager"):
        result = worker.process_scheduled_posts_once(poster=Poster(), now=datetime(2026, 10, 1, 11))
    saved = {row["id"]: row for row in load_posts_file(path)}
    assert result["claimed"] == count
    assert len(saved) == 5
    assert saved["p0"]["content_package_source"] == "concurrent-fixture"
    for i in range(count):
        assert saved[f"p{i}"]["status"] == "published"
        assert saved[f"p{i}"]["meta_upload_video_id"] == f"upload-page{i}"
        assert saved[f"p{i}"]["post_fb_id"] == f"reel-page{i}"
    assert output.joinpath("clip.mp4").exists() == (count < 4)
    assert worker.worker_status()["active_posts"] == 0
    assert load_publishing_settings(tmp_path)["posting_threads"] == threads


def test_workers_share_neither_page_nor_token_and_honor_cooldown(tmp_path):
    from web import scheduled_publisher as worker
    path = tmp_path / "posts.json"
    rows = [
        {"id": "one", "page_id": "a", "token_id": "token-a"},
        {"id": "same-token", "page_id": "b", "token_id": "token-a"},
        {"id": "same-page", "page_id": "a", "token_id": "token-b"},
        {"id": "cooldown", "page_id": "c", "token_id": "token-c"},
    ]
    for row in rows:
        row.update(status="scheduled", scheduled_time="2026-10-01 10:00:00")
    save_posts_file(path, rows)
    def entry(tid):
        return {"status": "ACTIVE", "rate_status": "COOLDOWN_80" if tid == "token-c" else "NORMAL"}
    def publish(post, *args):
        post["status"] = "published"
        return post
    with mock.patch.object(worker, "POSTS_FILE", path), \
         mock.patch("src.publisher.first_comment_queue.process_due_first_comments", return_value={}), \
         mock.patch("src.publisher.token_vault.TokenVault") as vault, \
         mock.patch("src.publisher.page_manager.PageManager"), \
         mock.patch.object(worker, "_publish_claimed_post", side_effect=publish) as called, \
         mock.patch.object(worker, "remove_posted_clip_file", return_value=False):
        vault.return_value.get_token_by_id.side_effect = entry
        result = worker.process_scheduled_posts_once(now=datetime(2026, 10, 1, 11))
    assert result["claimed"] == 1
    assert called.call_count == 1
    assert next(row for row in result["posts"] if row["id"] == "cooldown")["status"] == "scheduled"


@pytest.mark.parametrize("value", [0, 33, True, "4", None])
def test_invalid_thread_counts_do_not_replace_saved_settings(tmp_path, value):
    save_publishing_settings(tmp_path, 2)
    with pytest.raises(ValueError):
        save_publishing_settings(tmp_path, value)
    assert load_publishing_settings(tmp_path) == {"posting_threads": 2}


def test_settings_api_persists_parallelism(tmp_path):
    from web import app as appmod
    with mock.patch.object(appmod, "POSTS_FILE", tmp_path / "posts.json"):
        client = appmod.app.test_client()
        for threads in (1, 2, 4, 8):
            assert client.put("/api/publishing/settings", json={"posting_threads": threads}).status_code == 200
            assert client.get("/api/publishing/settings").get_json()["posting_threads"] == threads
        assert client.put("/api/publishing/settings", json={"posting_threads": 50}).status_code == 400


@pytest.fixture
def group_api(tmp_path, monkeypatch):
    from web import app as appmod
    from src.publisher.token_vault import TokenVault
    from src.publisher.page_manager import PageManager
    vault = TokenVault(tmp_path)
    pages = PageManager(tmp_path)
    monkeypatch.setattr(appmod, "token_vault", vault)
    monkeypatch.setattr(appmod, "page_manager", pages)
    monkeypatch.setattr(appmod, "POSTS_FILE", tmp_path / "posts.json")
    monkeypatch.setattr(appmod, "TOKEN_GROUPS_FILE", tmp_path / "token_groups.json")
    monkeypatch.setattr(appmod, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(appmod, "_ensure_recent_meta_health", lambda: None)
    tokens = [{"id": f"t{i}", "name": f"Fixture {i}", "token": f"fixture-secret-{i}", "status": "ACTIVE"} for i in range(2)]
    vault._save(tokens)
    return appmod, appmod.app.test_client(), vault, pages, tokens


def test_group_create_sync_source_snapshot_and_linked_selector(group_api):
    appmod, client, vault, pages, tokens = group_api
    def refresh(tid):
        token = next(t for t in tokens if t["id"] == tid)
        discovered = [{"id": "source-page", "access_token": "page-fixture", "tasks": ["CREATE_CONTENT"]}]
        if tid == "t1":
            discovered.append({"id": "other-page", "access_token": "other-fixture", "tasks": ["CREATE_CONTENT"]})
        return token, discovered
    with mock.patch.object(vault, "refresh_token_pages", side_effect=refresh):
        response = client.post("/api/token-groups", json={"name": "Operator's group", "token_ids": ["t0", "t1"],
            "page_source_token_id": "t0", "sync_pages": True, "create_page_group": True})
    assert response.status_code == 200
    group = response.get_json()["group"]
    assert group["page_ids"] == ["source-page"]
    listed = client.get("/api/token-groups").get_json()["groups"]
    assert listed[0]["id"] == group["id"]
    linked = client.get("/api/groups").get_json()["groups"][0]
    assert linked["token_group_id"] == group["id"]
    assert linked["page_ids"] == ["source-page"]
    with mock.patch.object(vault, "refresh_token_pages", side_effect=refresh):
        assert client.post(f"/api/token-groups/{group['id']}/sync-pages").get_json()["page_ids"] == ["source-page"]


def test_import_assigns_explicit_group_and_creates_linked_page_selector(group_api):
    appmod, client, vault, pages, tokens = group_api
    with mock.patch.object(vault, "verify_identity", return_value={"status": "ACTIVE", "owner_name": "Fixture owner"}):
        response = client.post("/api/tokens", json={"tokens_input": "new-token-fixture", "name": "Imported", "page_sync_mode": "none", "token_group_name": "Fresh group"})
    assert response.status_code == 200
    imported = response.get_json()
    tid = imported["results"][0]["id"]
    assert imported["token_group"]["token_ids"] == [tid]
    assert client.get("/api/token-groups").get_json()["groups"][0]["name"] == "Fresh group"
    assert client.get("/api/groups").get_json()["groups"][0]["name"] == "Fresh group"


def test_group_token_assignments_survive_global_page_reallocation(group_api):
    appmod, client, vault, pages, tokens = group_api
    for token in tokens:
        pages.sync_pages_from_token(token, [{"id": "page-a", "access_token": "page-" + token["id"], "tasks": ["CREATE_CONTENT"]}])
    appmod.save_token_groups([{"id": "g0", "name": "G0", "token_ids": ["t0"], "page_ids": ["page-a"]},
                             {"id": "g1", "name": "G1", "token_ids": ["t1"], "page_ids": ["page-a"]}])
    for gid in ("g0", "g1"):
        assert client.post("/api/pages/batch_assign_token", json={"token_group_id": gid}).status_code == 200
    assert pages.list_pages()[0]["token_id"] == "t1"
    first_group = appmod.load_token_groups()[0]
    assert appmod.page_in_token_group(pages.list_pages()[0], first_group)["token_id"] == "t0"
    bindings = client.get("/api/pages").get_json()["pages"][0]["group_token_assignments"]
    assert bindings == {"g0": "t0", "g1": "t1"}
    first_group["page_token_bindings"] = {"page-a": "outside-group"}
    assert appmod.page_in_token_group(pages.list_pages()[0], first_group)["token_id"] == ""


def test_native_handoffs_run_in_parallel_with_distinct_tokens_and_preserve_ids(tmp_path):
    from web import scheduled_publisher as worker
    path = tmp_path / "posts.json"
    rows = [{"id": f"p{i}", "page_id": f"page{i}", "token_id": f"t{i % 2}",
             "status": "meta_handoff", "scheduled_time": "2026-10-01 12:00:00"} for i in range(3)]
    save_posts_file(path, rows)
    save_publishing_settings(tmp_path, 2)
    barrier = threading.Barrier(2)
    def handoff(posts, save, *args, post_id=None, **kwargs):
        post = next(row for row in posts if row["id"] == post_id)
        post.update(status="processing", meta_video_id="meta-" + post_id)
        save(posts)
        barrier.wait(timeout=5)
        post["status"] = "meta_scheduled"
        save(posts)
        return 1
    with mock.patch.object(worker, "POSTS_FILE", path), \
         mock.patch("src.publisher.first_comment_queue.process_due_first_comments", return_value={}), \
         mock.patch("src.publisher.token_vault.TokenVault") as vault, \
         mock.patch("src.publisher.page_manager.PageManager"), \
         mock.patch("web.meta_handoff.process_next_handoff", side_effect=handoff):
        vault.return_value.get_token_by_id.return_value = {"status": "ACTIVE"}
        result = worker.process_scheduled_posts_once(now=datetime(2026, 10, 1, 11))
    assert result["handed_off"] == 2
    saved = {post["id"]: post for post in load_posts_file(path)}
    assert saved["p0"]["meta_video_id"] == "meta-p0"
    assert saved["p1"]["meta_video_id"] == "meta-p1"
    assert saved["p0"]["status"] == saved["p1"]["status"] == "meta_scheduled"
    assert saved["p2"]["status"] == "meta_handoff"


def test_native_handoffs_ignore_publish_gap_and_remote_processing_reservations(tmp_path):
    from web import scheduled_publisher as worker
    path = tmp_path / "posts.json"
    now = datetime(2026, 10, 1, 11)
    rows = [{"id": "remote", "page_id": "page-a", "token_id": "token-a", "status": "processing",
             "meta_next_check_at": now.timestamp() + 300, "meta_upload_video_id": "9001",
             "meta_handoff_started_at": "2026-10-01 10:59:00"},
            {"id": "next", "page_id": "page-a", "token_id": "token-a", "status": "meta_handoff",
             "scheduled_time": "2026-10-01 12:00:00", "token_gap_seconds": 900},
            {"id": "same-batch", "page_id": "page-a", "token_id": "token-a", "status": "meta_handoff",
             "scheduled_time": "2026-10-01 12:15:00"}]
    save_posts_file(path, rows)
    def handoff(posts, save, *args, post_id=None, **kwargs):
        post = next(row for row in posts if row["id"] == post_id)
        post.update(status="processing", meta_video_id="9002")
        save(posts)
        return 1
    with mock.patch.object(worker, "POSTS_FILE", path), \
         mock.patch("src.publisher.first_comment_queue.process_due_first_comments", return_value={}), \
         mock.patch("src.publisher.token_vault.TokenVault") as vault, \
         mock.patch("src.publisher.page_manager.PageManager"), \
         mock.patch("web.meta_handoff.process_next_handoff", side_effect=handoff) as called:
        vault.return_value.get_token_by_id.return_value = {"status": "ACTIVE"}
        result = worker.process_scheduled_posts_once(now=now)
    assert result["handed_off"] == 1 and called.call_count == 1
    saved = {row["id"]: row for row in load_posts_file(path)}
    assert saved["remote"]["meta_upload_video_id"] == "9001"
    assert saved["next"]["meta_video_id"] == "9002"
    assert saved["same-batch"]["status"] == "meta_handoff"


def test_expired_meta_handoff_falls_back_to_original_app_due_time(tmp_path):
    from web import scheduled_publisher as worker
    path = tmp_path / "posts.json"
    save_posts_file(path, [{"id": "late-meta", "status": "scheduled", "page_id": "fixture",
                          "scheduled_time": "2026-10-01 10:00:00", "requested_publish_mode": "meta_scheduled"}])
    with mock.patch.object(worker, "POSTS_FILE", path), \
         mock.patch("src.publisher.first_comment_queue.process_due_first_comments", return_value={}), \
         mock.patch("src.publisher.token_vault.TokenVault"), mock.patch("src.publisher.page_manager.PageManager"), \
         mock.patch.object(worker, "_publish_claimed_post", side_effect=lambda post, *args: post) as publish:
        result = worker.process_scheduled_posts_once(now=datetime(2026, 10, 1, 11))
    row = result["posts"][0]
    assert row["publish_mode"] == row["requested_publish_mode"] == "app_queue"
    assert row["original_requested_publish_mode"] == "meta_scheduled"
    assert row["meta_schedule_fallback"] == "app_queue"
    assert row["scheduled_time"] == "2026-10-01 10:00:00"
    publish.assert_called_once()


def test_processing_reel_is_still_verified_after_six_attempts_without_reupload(tmp_path):
    from web import scheduled_publisher as worker
    from src.publisher.meta_reel_poster import MetaReelPoster
    path = tmp_path / "posts.json"
    save_posts_file(path, [{"id": "slow-meta", "status": "processing", "page_id": "page-a", "token_id": "token-a",
                          "meta_upload_video_id": "123456", "meta_reconcile_version": 2, "meta_reconcile_attempts": 6}])
    with mock.patch.object(worker, "POSTS_FILE", path), \
         mock.patch("src.publisher.first_comment_queue.process_due_first_comments", return_value={}), \
         mock.patch("src.publisher.token_vault.TokenVault"), \
         mock.patch("src.publisher.page_manager.PageManager") as pages, \
         mock.patch("src.publisher.meta_preflight.preflight_pages", return_value={"ok": True, "ready": [{"token": "fixture", "token_id": "token-a"}]}), \
         mock.patch.object(MetaReelPoster, "check_processing_reel", return_value={"verified": True, "video_id": "123456"}) as check, \
         mock.patch.object(worker, "_record_posted_clip"), \
         mock.patch.object(worker, "remove_posted_clip_file", return_value=False):
        pages.return_value.list_pages.return_value = [{"page_id": "page-a"}]
        poster = mock.Mock()
        result = worker.process_scheduled_posts_once(poster=poster, now=datetime(2026, 10, 1, 11))
    check.assert_called_once()
    assert result["posts"][0]["status"] == "published"
    assert result["posts"][0]["post_fb_id"] == "123456"
    poster.publish_reel.assert_not_called()
