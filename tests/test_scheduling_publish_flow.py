import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock


class SchedulingPublishFlowTests(unittest.TestCase):
    def test_immediate_publish_requires_website_article_url(self):
        from web import app as web_app

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"video")
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app.page_manager, "list_pages", return_value=[self._verified_page()]
            ), mock.patch.object(web_app.page_manager, "list_groups", return_value=[]), mock.patch.object(
                web_app.reel_poster, "publish_reel"
            ) as publish:
                response = web_app.app.test_client().post("/api/publish/reel", json={
                    "page_id": "page-1", "filename": "clip.mp4", "first_comment": "Read more",
                })
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.get_json()["code"], "website_article_required")
            publish.assert_not_called()

    def test_immediate_comment_failure_queues_retry_with_website_link(self):
        from web import app as web_app
        from src.publisher import first_comment_queue

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"video")
            posts_file = root / "posts.json"
            queue_file = root / "comments.json"
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app, "POSTS_FILE", posts_file
            ), mock.patch.object(first_comment_queue, "QUEUE_FILE", queue_file), mock.patch.object(
                web_app.page_manager, "list_pages", return_value=[self._verified_page()]
            ), mock.patch.object(web_app.page_manager, "list_groups", return_value=[]), mock.patch.object(
                web_app.page_manager, "save_pages"
            ), mock.patch.object(web_app.token_vault, "get_token_by_id", return_value=self._credential_entry()), mock.patch.object(
                web_app.reel_poster, "publish_reel", return_value={
                    "success": True, "video_id": "reel-1", "status": "PUBLISHED",
                    "comment_result": {"success": False, "error": "Meta busy"},
                }
            ) as publish, mock.patch("web.scheduled_publisher._record_posted_clip"), mock.patch(
                "web.scheduled_publisher.remove_posted_clip_file", return_value=False
            ):
                response = web_app.app.test_client().post("/api/publish/reel", json={
                    "page_id": "page-1", "filename": "clip.mp4", "first_comment": "Read more",
                    "article_url": "https://example.test/article",
                })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()["results"][0]["first_comment_status"], "pending_retry")
            saved = json.loads(posts_file.read_text(encoding="utf-8"))[0]
            queued = json.loads(queue_file.read_text(encoding="utf-8"))[0]
            self.assertEqual(saved["status"], "published")
            self.assertEqual(saved["first_comment_status"], "pending_retry")
            self.assertEqual(saved["first_comment_queue_id"], queued["id"])
            self.assertEqual(queued["post_id"], saved["id"])
            self.assertIn("https://example.test/article", queued["comment_text"])
            self.assertEqual(publish.call_args.kwargs["first_comment"], queued["comment_text"])

    def test_schedule_click_enqueues_priority_and_starts_worker_after_persist(self):
        from web import app as web_app
        from src import content_packages as cp

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"video")
            posts_file = root / "posts.json"
            queue = root / "content_packages.json"
            queue.write_text(json.dumps([{
                "id": "old-library-work", "clip_filename": "other.mp4", "status": "queued",
            }]), encoding="utf-8")

            def check_worker_start():
                entries = json.loads(posts_file.read_text(encoding="utf-8"))
                items = json.loads(queue.read_text(encoding="utf-8"))
                self.assertEqual(entries[0]["content_package_id"], items[0]["id"])
                self.assertTrue(items[0]["schedule_priority"])
                self.assertEqual(items[1]["id"], "old-library-work")

            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app, "POSTS_FILE", posts_file
            ), mock.patch.object(cp, "QUEUE_FILE", queue), mock.patch.object(
                web_app.page_manager, "list_pages", return_value=[self._verified_page()]
            ), mock.patch.object(web_app.page_manager, "list_groups", return_value=[]), mock.patch.object(
                web_app.token_vault, "get_token_by_id", return_value=self._credential_entry()
            ), mock.patch.object(web_app, "get_clip_metadata", return_value={}), mock.patch.object(
                web_app, "start_content_package_worker", side_effect=check_worker_start
            ) as start, mock.patch.object(web_app.reel_poster, "publish_reel") as publish:
                response = web_app.app.test_client().post("/api/publish/reel", json={
                    "page_id": "page-1", "filename": "clip.mp4", "title": "Fixture",
                    "auto_first_comment": True, "schedule_time": "2099-01-02T03:04",
                })
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.get_json()["success"])
            start.assert_called_once()
            publish.assert_not_called()

    def test_scheduled_package_prioritized_without_processing_in_http(self):
        from web import app as web_app
        from src import content_packages as cp

        with tempfile.TemporaryDirectory() as folder:
            queue = Path(folder) / "content_packages.json"
            queue.write_text(json.dumps([
                {"id": "library", "status": "queued"},
                {"id": "already-running", "status": "running"},
                {"id": "scheduled", "status": "queued"},
            ]), encoding="utf-8")
            with mock.patch.object(cp, "QUEUE_FILE", queue), mock.patch.object(
                cp, "process_content_packages_once", side_effect=AssertionError("HTTP must not process")
            ):
                web_app.prioritize_scheduled_packages({"scheduled"})
            items = json.loads(queue.read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in items], ["scheduled", "library", "already-running"])
            self.assertTrue(items[0]["schedule_priority"])

    def test_direct_schedule_reuses_ready_studio_package_without_new_worker(self):
        from web import app as web_app
        from src import content_packages as cp

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"video")
            posts_file = root / "posts.json"
            queue = root / "content_packages.json"
            queue.write_text(json.dumps([{
                "id": "studio-ready", "clip_filename": str(output / "clip.mp4"),
                "status": "ready", "article_url": "https://example.test/article",
                "website_status": "ready", "result": {
                    "caption": "Prepared caption", "hero_title": "Prepared title",
                    "first_comment": "Read https://example.test/article", "source": "fixture",
                },
            }]), encoding="utf-8")
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app, "POSTS_FILE", posts_file
            ), mock.patch.object(cp, "DATA_ROOT", root), mock.patch.object(
                cp, "QUEUE_FILE", queue
            ), mock.patch.object(web_app.page_manager, "list_pages", return_value=[self._verified_page()]), mock.patch.object(
                web_app.page_manager, "list_groups", return_value=[]
            ), mock.patch.object(web_app.token_vault, "get_token_by_id", return_value=self._credential_entry()), mock.patch.object(
                web_app, "get_clip_metadata", return_value={}
            ), mock.patch.object(web_app, "start_content_package_worker") as start, mock.patch.object(
                web_app.reel_poster, "publish_reel"
            ) as publish:
                response = web_app.app.test_client().post("/api/publish/reel", json={
                    "page_id": "page-1", "filename": "clip.mp4", "title": "Original title",
                    "auto_first_comment": True, "schedule_time": "2099-01-02T03:04",
                })
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.get_json()["success"])
            saved = json.loads(posts_file.read_text(encoding="utf-8"))[0]
            self.assertEqual(saved["content_package_id"], "studio-ready")
            self.assertEqual(saved["content_package_status"], "ready")
            self.assertEqual(saved["article_url"], "https://example.test/article")
            self.assertEqual(saved["first_comment"], "Read https://example.test/article")
            self.assertEqual(saved["content"], "Prepared caption")
            self.assertEqual(len(json.loads(queue.read_text(encoding="utf-8"))), 1)
            start.assert_not_called()
            publish.assert_not_called()

    def test_direct_schedule_attaches_queued_fallback_without_using_draft(self):
        from web import app as web_app
        from src import content_packages as cp

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"video")
            posts_file = root / "posts.json"
            queue = root / "content_packages.json"
            queue.write_text(json.dumps([{
                "id": "studio-pending", "clip_filename": str(output / "clip.mp4"),
                "title": "Fixture", "status": "queued", "article_url": "https://example.test/article",
                "website_status": "ready", "result": {
                    "caption": "Draft caption", "hero_title": "Draft title",
                    "first_comment": "Read https://example.test/article", "source": "no_llm_error_fallback",
                },
            }]), encoding="utf-8")
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app, "POSTS_FILE", posts_file
            ), mock.patch.object(cp, "DATA_ROOT", root), mock.patch.object(
                cp, "QUEUE_FILE", queue
            ), mock.patch.object(web_app.page_manager, "list_pages", return_value=[self._verified_page()]), mock.patch.object(
                web_app.page_manager, "list_groups", return_value=[]
            ), mock.patch.object(web_app.token_vault, "get_token_by_id", return_value=self._credential_entry()), mock.patch.object(
                web_app, "get_clip_metadata", return_value={}
            ), mock.patch.object(web_app, "start_content_package_worker") as start, mock.patch.object(
                web_app.reel_poster, "publish_reel"
            ) as publish:
                response = web_app.app.test_client().post("/api/publish/reel", json={
                    "page_id": "page-1", "filename": "clip.mp4", "title": "Original title",
                    "auto_first_comment": True, "schedule_time": "2099-01-02T03:04",
                })
            self.assertEqual(response.status_code, 200)
            saved = json.loads(posts_file.read_text(encoding="utf-8"))[0]
            self.assertEqual(saved["content_package_id"], "studio-pending")
            self.assertEqual(saved["content_package_status"], "queued")
            self.assertEqual(saved["website_status"], "pending_generation")
            self.assertEqual(saved["content"], "")
            self.assertEqual(len(json.loads(queue.read_text(encoding="utf-8"))), 1)
            start.assert_called_once()
            publish.assert_not_called()

    def test_meta_page_task_aliases_accept_publish_capability_but_readonly_tasks_fail(self):
        from src.publisher.meta_preflight import resolve_page_token

        class Vault:
            def __init__(self, entry): self.entry = entry
            def get_token_by_id(self, _token_id): return self.entry

        class Manager:
            def __init__(self, tasks): self.tasks = tasks
            def resolve_verified_mapping(self, page_id, _entry):
                return ({"token_id": "tok_verified", "page_token": "page-token", "tasks": self.tasks}, None)

        page = {"page_id": "page-1", "page_name": "Page One", "token_id": "tok_verified"}
        credential = {"id": "tok_verified", "name": "Test", "token": "cred", "status": "ACTIVE"}
        self.assertTrue(resolve_page_token(page, Vault(credential), Manager(["PROFILE_PLUS_MANAGE"]))["ok"])
        blocked = resolve_page_token(page, Vault(credential), Manager(["ANALYZE", "ADVERTISE"]))
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "publish_capability_missing")

    @staticmethod
    def _verified_page(page_id="page-1", page_name="Page One", token_id="tok_verified", page_token="page-token-verified"):
        """Build a Page record whose token binding is discovery-backed.

        Schedule endpoints fail closed unless a Page has an exact Meta-verified
        binding, so fixtures must mirror what ``/me/accounts`` sync produces.
        """
        from src.publisher.page_manager import PageManager

        fingerprint = PageManager.credential_fingerprint("fixture-credential")
        binding = {
            "token_id": token_id,
            "token_name": "Fixture System User",
            "page_token": page_token,
            "verified_page_id": page_id,
            "verified_at": "2026-09-28 12:00:00",
            "credential_fingerprint": fingerprint,
            "tasks": ["CREATE_CONTENT", "MANAGE"],
            "status": "VERIFIED",
        }
        return {
            "page_id": page_id,
            "page_name": page_name,
            "page_token": page_token,
            "token_id": token_id,
            "token_name": "Fixture System User",
            "token_bindings": {token_id: binding},
            "mapping_status": "VERIFIED",
            "mapping_verified_at": "2026-09-28 12:00:00",
            "status": "ACTIVE",
        }

    @staticmethod
    def _credential_entry(token_id="tok_verified"):
        return {
            "id": token_id,
            "name": "Fixture System User",
            "token": "fixture-credential",
            "status": "ACTIVE",
        }

    def test_meta_reel_start_upload_finish_flow_is_mocked_and_records_object_id(self):
        from src.publisher.meta_reel_poster import MetaReelPoster
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "clip.mp4"
            video.write_bytes(b"fixture")
            responses = [
                mock.Mock(status_code=200, ok=True, headers={}, json=lambda: {"video_id": "video-1", "upload_url": "https://upload.test/video-1"}),
                mock.Mock(status_code=200, ok=True, headers={}, json=lambda: {}),
                mock.Mock(status_code=200, ok=True, headers={}, json=lambda: {"success": True, "video_id": "video-1", "permalink_url": "https://facebook.test/reel/video-1"}),
            ]
            with mock.patch("src.publisher.meta_reel_poster.requests.post", side_effect=responses) as post:
                result = MetaReelPoster().publish_reel("page-1", "page-token", video)
        self.assertTrue(result["success"])
        self.assertEqual(result["video_id"], "video-1")
        self.assertEqual(post.call_count, 3)
        self.assertEqual(post.call_args_list[0].args[0], "https://graph.facebook.com/v22.0/page-1/video_reels")
        self.assertIn("upload.test", post.call_args_list[1].args[0])
        self.assertEqual(post.call_args_list[2].args[0], "https://graph.facebook.com/v22.0/page-1/video_reels")

    def test_meta_reel_finish_without_object_id_is_unknown(self):
        from src.publisher.meta_reel_poster import MetaReelPoster
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "clip.mp4"
            video.write_bytes(b"fixture")
            responses = [
                mock.Mock(status_code=200, ok=True, headers={}, json=lambda: {"video_id": "video-1", "upload_url": "https://upload.test/video-1"}),
                mock.Mock(status_code=200, ok=True, headers={}, json=lambda: {}),
                mock.Mock(status_code=200, ok=True, headers={}, json=lambda: {"success": True}),
            ]
            with mock.patch("src.publisher.meta_reel_poster.requests.post", side_effect=responses):
                result = MetaReelPoster().publish_reel("page-1", "page-token", video)
        self.assertFalse(result["success"])
        self.assertTrue(result["outcome_unknown"])

    def test_meta_finish_post_id_is_processing_candidate_not_published(self):
        from src.publisher.meta_reel_poster import MetaReelPoster
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "clip.mp4"
            video.write_bytes(b"fixture")
            responses = [
                mock.Mock(status_code=200, ok=True, headers={}, json=lambda: {"video_id": "upload-1", "upload_url": "https://upload.test/1"}),
                mock.Mock(status_code=200, ok=True, headers={}, json=lambda: {}),
                mock.Mock(status_code=200, ok=True, headers={}, json=lambda: {"success": True, "message": "Video is Processing...check upload status", "post_id": "122117668215471152"}),
            ]
            with mock.patch("src.publisher.meta_reel_poster.requests.post", side_effect=responses) as post:
                result = MetaReelPoster().publish_reel("page-1", "page-token", video, first_comment="Do not send")
        self.assertFalse(result["success"])
        self.assertTrue(result["processing"])
        self.assertEqual(result["meta_post_id"], "122117668215471152")
        self.assertNotIn("fb_url", result)
        self.assertEqual(post.call_count, 3)

    def test_read_only_reconciliation_requires_explicit_ready_and_permalink(self):
        from src.publisher.meta_reel_poster import MetaReelPoster
        poster = MetaReelPoster()
        response = mock.Mock(ok=True, headers={}, json=lambda: {"id": "123", "status": {"video_status": "processing"}, "permalink_url": "https://facebook.test/reel/123"})
        with mock.patch("src.publisher.meta_reel_poster.requests.get", return_value=response) as get, mock.patch("src.publisher.meta_reel_poster.requests.post") as post:
            self.assertFalse(poster.check_processing_reel("123", "fixture-token")["verified"])
            response.json = lambda: {"id": "123", "status": {"video_status": "ready", "publishing_phase": {"publish_status": "published"}}, "permalink_url": "/reel/123/"}
            self.assertTrue(poster.check_processing_reel("123", "fixture-token")["verified"])
            post.assert_not_called()
            self.assertEqual(get.call_count, 2)

    def test_invalid_schedule_time_is_rejected_without_immediate_publish(self):
        from web import app as web_app

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"video")
            client = web_app.app.test_client()
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app.token_vault, "get_token_by_id", return_value=self._credential_entry()
            ), mock.patch.object(web_app.page_manager, "list_pages", return_value=[self._verified_page()]), mock.patch.object(
                web_app.page_manager, "list_groups", return_value=[]
            ), mock.patch.object(web_app.reel_poster, "publish_reel") as publish:
                response = client.post("/api/publish/reel", json={
                    "page_id": "page-1", "filename": "clip.mp4", "schedule_time": "not-a-time",
                })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "invalid_schedule_time")
        publish.assert_not_called()

    def test_schedule_rejects_foreign_absolute_video_even_if_output_has_same_basename(self):
        from web import app as web_app

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"unrelated")
            foreign = root / "elsewhere" / "clip.mp4"
            foreign.parent.mkdir()
            foreign.write_bytes(b"requested")
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app.reel_poster, "publish_reel"
            ) as publish:
                response = web_app.app.test_client().post("/api/publish/reel", json={
                    "page_id": "page-1", "filename": str(foreign), "schedule_time": "2099-01-02 03:04",
                })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "invalid_video_path")
        publish.assert_not_called()

    def test_batch_stages_explicit_foreign_folder_without_basename_substitution(self):
        from web import app as web_app

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            foreign = root / "foreign"
            output.mkdir()
            foreign.mkdir()
            (foreign / "clip.mp4").write_bytes(b"foreign")
            (output / "clip.mp4").write_bytes(b"unrelated")
            group = {"id": "group-1", "name": "Group", "page_ids": ["page-1"],
                     "folder_binding": str(foreign), "schedule_config": {"times": ["23:59"]}}
            posts_file = root / "posts.json"
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app, "BASE_DIR", root
            ), mock.patch.object(web_app, "POSTS_FILE", posts_file), mock.patch.object(
                web_app.page_manager, "list_groups", return_value=[group]
            ), mock.patch.object(web_app.page_manager, "list_pages", return_value=[self._verified_page()]), mock.patch.object(
                web_app.token_vault, "get_token_by_id", return_value=self._credential_entry()
            ):
                response = web_app.app.test_client().post("/api/distribute/batch", json={
                    "group_id": "group-1", "posts_per_page": 1, "clip_filenames": ["clip.mp4"],
                })
            self.assertEqual(response.status_code, 200, response.get_json())
            post = json.loads(posts_file.read_text(encoding="utf-8"))[0]
            self.assertEqual(post["source_video_path"], str((foreign / "clip.mp4").resolve()))
            self.assertEqual(post["source_sha256"], __import__("hashlib").sha256(b"foreign").hexdigest())
            self.assertNotEqual(post["media_file"], "clip.mp4")
            self.assertEqual((output / post["media_file"]).read_bytes(), b"foreign")
            self.assertEqual((output / "clip.mp4").read_bytes(), b"unrelated")

    def test_batch_repairs_missing_legacy_default_output_folder(self):
        from web import app as web_app

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            group = {"id": "group-1", "name": "Group", "page_ids": ["page-1"],
                     "folder_binding": r"D:\Highlight_Video_Studio\output"}
            groups = [group]
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app, "BASE_DIR", root
            ), mock.patch.object(web_app.page_manager, "list_groups", return_value=groups), mock.patch.object(
                web_app.page_manager, "save_groups"
            ) as save_groups, mock.patch.object(web_app.page_manager, "list_pages", return_value=[self._verified_page()]), mock.patch.object(
                web_app.token_vault, "get_token_by_id", return_value=self._credential_entry()
            ):
                response = web_app.app.test_client().post("/api/distribute/batch", json={
                    "group_id": "group-1", "posts_per_page": 1,
                })
            self.assertNotEqual(response.get_json().get("code"), "missing_output_folder")
            self.assertEqual(group["folder_binding"], str(output))
            save_groups.assert_called_once()

    def test_batch_rejects_traversal_before_staging_or_saving(self):
        from web import app as web_app

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output, selected = root / "output", root / "selected"
            output.mkdir()
            selected.mkdir()
            (root / "clip.mp4").write_bytes(b"outside")
            group = {"id": "group-1", "page_ids": ["page-1"], "folder_binding": str(selected)}
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app, "BASE_DIR", root
            ), mock.patch.object(web_app.page_manager, "list_groups", return_value=[group]), mock.patch.object(
                web_app.page_manager, "list_pages", return_value=[self._verified_page()]
            ), mock.patch.object(web_app.token_vault, "get_token_by_id", return_value=self._credential_entry()), mock.patch.object(
                web_app, "save_posts"
            ) as save:
                response = web_app.app.test_client().post("/api/distribute/batch", json={
                    "group_id": "group-1", "posts_per_page": 1, "clip_filenames": ["../clip.mp4"],
                })
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.get_json()["code"], "invalid_video_path")
            self.assertEqual(list(output.iterdir()), [])
            save.assert_not_called()

    def test_batch_source_ledger_blocks_repeat_after_staging(self):
        from web import app as web_app

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output, selected = root / "output", root / "selected"
            output.mkdir()
            selected.mkdir()
            clip = selected / "clip.mp4"
            clip.write_bytes(b"video")
            (root / "posted_clips.json").write_text(json.dumps([str(clip.resolve())]), encoding="utf-8")
            group = {"id": "group-1", "page_ids": ["page-1"], "folder_binding": str(selected)}
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app, "BASE_DIR", root
            ), mock.patch.object(web_app.page_manager, "list_groups", return_value=[group]), mock.patch.object(
                web_app.page_manager, "list_pages", return_value=[self._verified_page()]
            ), mock.patch.object(web_app.token_vault, "get_token_by_id", return_value=self._credential_entry()), mock.patch.object(
                web_app, "save_posts"
            ) as save:
                response = web_app.app.test_client().post("/api/distribute/batch", json={
                    "group_id": "group-1", "posts_per_page": 1, "clip_filenames": ["clip.mp4"],
                })
            self.assertEqual(response.status_code, 400)
            self.assertEqual(list(output.iterdir()), [])
            save.assert_not_called()

    def test_schedule_payload_persists_comment_website_and_never_calls_meta(self):
        from web import app as web_app

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"video")
            posts_file = root / "posts.json"
            pages = [self._verified_page()]
            client = web_app.app.test_client()
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app, "POSTS_FILE", posts_file
            ), mock.patch.object(
                web_app, "load_posts", return_value=[]
            ), mock.patch.object(
                web_app.token_vault, "get_token_by_id", return_value=self._credential_entry()
            ), mock.patch.object(web_app.page_manager, "list_pages", return_value=pages), mock.patch.object(
                web_app.page_manager, "list_groups", return_value=[]
            ), mock.patch.object(web_app.reel_poster, "publish_reel") as publish:
                response = client.post("/api/publish/reel", json={
                    "page_id": "page-1",
                    "filename": "clip.mp4",
                    "title": "Fixture title",
                    "caption": "Fixture caption",
                    "first_comment": "Configured comment",
                    "article_url": "https://example.test/article",
                    "schedule_time": "2099-01-02T03:04",
                })
            self.assertEqual(response.status_code, 200)
            publish.assert_not_called()
            saved = json.loads(posts_file.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["first_comment"], "Configured comment\nhttps://example.test/article")
        self.assertEqual(saved[0]["first_comment_status"], "ready")
        self.assertEqual(saved[0]["article_url"], "https://example.test/article")
        self.assertEqual(saved[0]["website_status"], "ready")
        self.assertEqual(saved[0]["status"], "scheduled")
        self.assertEqual(saved[0]["token"], "page-token-verified")
        self.assertEqual(saved[0]["token_id"], "tok_verified")

    def test_batch_schedule_marks_generated_fields_pending_instead_of_missing(self):
        from web import app as web_app
        from src import content_packages as cp

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"video")
            posts_file = root / "posts.json"
            groups = [{
                "id": "group-1", "name": "Group", "page_ids": ["page-1"],
                "folder_binding": str(output), "schedule_config": {"times": ["23:59"], "stagger_minutes": 15},
            }]
            pages = [self._verified_page()]
            client = web_app.app.test_client()
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app, "POSTS_FILE", posts_file
            ), mock.patch.object(web_app, "BASE_DIR", root), mock.patch.object(
                web_app.page_manager, "list_groups", return_value=groups
            ), mock.patch.object(web_app.page_manager, "list_pages", return_value=pages), mock.patch.object(
                web_app.token_vault, "get_token_by_id", return_value=self._credential_entry()
            ), mock.patch.object(
                web_app, "get_clip_metadata", return_value={"video_title": "Fixture title"}
            ), mock.patch.object(cp, "QUEUE_FILE", root / "content_packages.json"), mock.patch.object(
                cp, "DATA_ROOT", root
            ), mock.patch.object(web_app, "start_content_package_worker"):
                response = client.post("/api/distribute/batch", json={
                    "group_id": "group-1", "posts_per_page": 1, "auto_first_comment": True,
                })
            self.assertEqual(response.status_code, 200)
            saved = json.loads(posts_file.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["content_package_status"], "queued")
        self.assertEqual(saved[0]["website_status"], "pending_generation")
        self.assertEqual(saved[0]["article_url"], "")
        self.assertEqual(saved[0]["token"], "page-token-verified")

    def test_schedule_cms_failure_is_recorded_without_dropping_facebook_queue(self):
        from web import app as web_app

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"video")
            posts_file = root / "posts.json"
            pages = [self._verified_page()]
            client = web_app.app.test_client()
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app, "POSTS_FILE", posts_file
            ), mock.patch.object(web_app, "load_posts", return_value=[]), mock.patch.object(
                web_app.token_vault, "get_token_by_id", return_value=self._credential_entry()
            ), mock.patch.object(web_app.page_manager, "list_pages", return_value=pages), mock.patch.object(
                web_app.page_manager, "list_groups", return_value=[]
            ), mock.patch.object(
                web_app, "publish_clip_to_website_cms", side_effect=RuntimeError("CMS upload unavailable")
            ), mock.patch.object(web_app.reel_poster, "publish_reel") as publish:
                response = client.post("/api/publish/reel", json={
                    "page_id": "page-1", "filename": "clip.mp4", "title": "Fixture title",
                    "caption": "Fixture caption", "auto_first_comment": True,
                    "schedule_time": "2099-01-02T03:04",
                })
            publish.assert_not_called()
            saved = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        self.assertEqual(saved["status"], "scheduled")
        self.assertEqual(saved["website_status"], "pending_generation")
        self.assertEqual(saved["content_package_status"], "queued")
        self.assertEqual(saved["website_error"], "")

    def test_manual_website_retry_updates_article_without_touching_facebook_schedule(self):
        from web import app as web_app

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            posts_file = Path(folder) / "posts.json"
            posts_file.write_text(json.dumps([{
                "id": "post-1", "status": "scheduled", "scheduled_time": "2099-01-02 03:04:00",
                "page_id": "page-1", "token": "fixture-token", "media_file": "clip.mp4",
                "title": "Fixture title", "auto_first_comment": True,
                "website_status": "failed", "website_error": "old failure",
                "article_url": "", "first_comment": "", "first_comment_status": "generation_failed",
            }]), encoding="utf-8")
            client = web_app.app.test_client()
            with mock.patch.object(web_app, "POSTS_FILE", posts_file), mock.patch.object(
                web_app, "publish_clip_to_website_cms", return_value=("https://example.test/retried", "")
            ), mock.patch.object(
                web_app, "generate_curiosity_comment_with_llm", return_value="Read https://example.test/retried"
            ), mock.patch.object(web_app.reel_poster, "publish_reel") as publish:
                response = client.post("/api/posts/post-1/retry-website")
            saved = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        self.assertEqual(response.status_code, 200)
        publish.assert_not_called()
        self.assertEqual(saved["status"], "scheduled")
        self.assertEqual(saved["scheduled_time"], "2099-01-02 03:04:00")
        self.assertEqual(saved["article_url"], "https://example.test/retried")
        self.assertEqual(saved["website_status"], "ready")

    def test_worker_reuses_saved_article_without_duplicate_website_publish(self):
        from src.publisher import first_comment_queue
        from web import scheduled_publisher as worker

        calls = []

        class Poster:
            def publish_reel(self, **kwargs):
                calls.append(("publish", kwargs["first_comment"]))
                return {"success": True, "video_id": "video-123", "fb_url": "https://facebook.test/reel/123"}

            def post_first_comment(self, object_id, page_token, comment_text, token_id=None):
                calls.append(("comment", object_id, comment_text))
                return {"success": True, "comment_id": "comment-1"}

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"video")
            posts_file = root / "posts.json"
            posted_file = root / "posted.json"
            queue_file = root / "queue.json"
            posts_file.write_text(json.dumps([{
                "id": "post-1", "status": "scheduled", "scheduled_time": "2026-01-01 00:00:00",
                "page_id": "page-1", "page_name": "Page One", "token": "fixture-token",
                "media_file": "clip.mp4", "title": "Title", "content": "Caption",
                "auto_first_comment": True, "use_llm_comment": True,
                "article_url": "https://example.test/article", "website_status": "ready",
                "first_comment": "Read: https://example.test/article", "first_comment_status": "ready",
            }]), encoding="utf-8")
            website_publish = mock.Mock(side_effect=AssertionError("due-time CMS publish must not run"))
            comment_generate = mock.Mock(side_effect=AssertionError("due-time comment generation must not run"))
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "POSTED_CLIPS_FILE", posted_file
            ), mock.patch.object(worker, "OUTPUT_DIR", output), mock.patch.object(
                first_comment_queue, "QUEUE_FILE", queue_file
            ):
                result = worker.process_scheduled_posts_once(
                    poster=Poster(), now=datetime(2026, 1, 1, 1, 0, 0),
                    website_publisher=website_publish, comment_generator=comment_generate,
                )
        post = result["posts"][0]
        self.assertEqual(calls[0], ("publish", ""))
        self.assertEqual(calls[1][0], "comment")
        self.assertEqual(post["status"], "published")
        self.assertEqual(post["article_url"], "https://example.test/article")
        self.assertEqual(post["fb_url"], "https://facebook.test/reel/123")
        self.assertEqual(post["first_comment_status"], "posted")
        website_publish.assert_not_called()
        comment_generate.assert_not_called()

    def test_worker_waits_for_website_after_saved_website_failure(self):
        from src.publisher import first_comment_queue
        from web import scheduled_publisher as worker

        class Poster:
            def publish_reel(self, **kwargs):
                return {"success": True, "video_id": "video-website-failed"}

            def post_first_comment(self, *args, **kwargs):
                raise AssertionError("No comment exists after website failure")

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"video")
            posts_file = root / "posts.json"
            posts_file.write_text(json.dumps([{
                "id": "post-1", "status": "scheduled", "scheduled_time": "2026-01-01 00:00:00",
                "page_id": "page-1", "token": "fixture-token", "media_file": "clip.mp4",
                "title": "Title", "content": "Caption", "auto_first_comment": True,
                "website_status": "failed", "website_error": "CMS unavailable",
                "first_comment": "", "first_comment_status": "generation_failed",
            }]), encoding="utf-8")
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "POSTED_CLIPS_FILE", root / "posted.json"
            ), mock.patch.object(worker, "OUTPUT_DIR", output), mock.patch.object(
                first_comment_queue, "QUEUE_FILE", root / "queue.json"
            ):
                result = worker.process_scheduled_posts_once(
                    poster=Poster(), now=datetime(2026, 1, 1, 1, 0, 0),
                    website_publisher=mock.Mock(side_effect=AssertionError("must not retry automatically")),
                )
        post = result["posts"][0]
        self.assertEqual(post["status"], "failed")
        self.assertEqual(post["retry_stage"], "website_content")
        self.assertFalse(post.get("post_fb_id"))
        self.assertEqual(post["website_status"], "failed")

    def test_comment_failure_is_explicit_and_retryable(self):
        from src.publisher import first_comment_queue
        from web import scheduled_publisher as worker

        class Poster:
            def publish_reel(self, **kwargs):
                return {"success": True, "video_id": "video-123"}

            def post_first_comment(self, *args, **kwargs):
                return {"success": False, "error": "temporary comment error"}

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"video")
            posts_file = root / "posts.json"
            queue_file = root / "queue.json"
            posts_file.write_text(json.dumps([{
                "id": "post-1", "status": "scheduled", "scheduled_time": "2026-01-01 00:00:00",
                "page_id": "page-1", "token": "fixture-token", "media_file": "clip.mp4",
                "title": "Title", "content": "Caption", "auto_first_comment": False,
                "first_comment": "Configured comment",
            }]), encoding="utf-8")
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "POSTED_CLIPS_FILE", root / "posted.json"
            ), mock.patch.object(worker, "OUTPUT_DIR", output), mock.patch.object(
                first_comment_queue, "QUEUE_FILE", queue_file
            ):
                result = worker.process_scheduled_posts_once(poster=Poster(), now=datetime(2026, 1, 1, 1, 0, 0))
                queued = json.loads(queue_file.read_text(encoding="utf-8"))
        post = result["posts"][0]
        self.assertEqual(post["status"], "published")
        self.assertEqual(post["first_comment_status"], "pending_retry")
        self.assertIn("temporary", post["first_comment_error"])
        self.assertEqual(queued[0]["post_id"], "post-1")

    def test_posts_api_and_video_endpoint_expose_safe_preview_download_and_facebook_url(self):
        from web import app as web_app

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"fixture-video")
            posts_file = root / "posts.json"
            posts_file.write_text(json.dumps([{
                "id": "post-1", "status": "published", "media_file": "clip.mp4", "post_fb_id": "video-123"
            }]), encoding="utf-8")
            client = web_app.app.test_client()
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(web_app, "POSTS_FILE", posts_file):
                listed = client.get("/api/posts").get_json()[0]
                preview = client.get(listed["local_video_url"], buffered=True)
                download = client.get(listed["local_download_url"], buffered=True)
                traversal = client.get("/api/clips/play/..%2Fsecret.mp4", buffered=True)
                preview.close()
                download.close()
                traversal.close()
        self.assertTrue(listed["local_video_available"])
        self.assertEqual(listed["fb_url"], "https://www.facebook.com/reel/video-123")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(download.status_code, 200)
        self.assertIn("attachment", download.headers.get("Content-Disposition", ""))
        self.assertIn(traversal.status_code, (400, 404))

    def test_ui_distinguishes_pending_failed_and_not_configured_semantics(self):
        root = Path(__file__).resolve().parent.parent
        html = (root / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Chờ tạo khi đến giờ đăng", html)
        self.assertIn("Lỗi First Comment · sẽ thử lại", html)
        self.assertIn("Không cấu hình", html)
        self.assertIn("Mở bài website", html)
        self.assertIn("Xem video", html)


    def test_content_batch_skips_posted_and_existing_packages(self):
        from web import app as web_app
        from src import content_packages

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            clip_posted = root / "posted.mp4"
            clip_queued = root / "queued.mp4"
            clip_new = root / "new.mp4"
            for clip in (clip_posted, clip_queued, clip_new):
                clip.write_bytes(b"video")
            posted_file = root / "posted_clips.json"
            posted_file.write_text(json.dumps([str(clip_posted)]), encoding="utf-8")
            queue_file = root / "content_packages.json"
            queue_file.write_text(json.dumps([{"id": "p1", "clip_filename": str(clip_queued), "status": "queued"}]), encoding="utf-8")
            client = web_app.app.test_client()
            with mock.patch.object(web_app, "BASE_DIR", root), mock.patch.object(
                web_app, "POSTS_FILE", root / "posts.json"
            ), mock.patch.object(content_packages, "QUEUE_FILE", queue_file
            ), mock.patch.object(web_app, "list_packages", return_value=[{"id": "p1", "clip_filename": str(clip_queued), "status": "queued"}]
            ), mock.patch.object(web_app, "get_clip_metadata", return_value={"video_title": "New"}
            ), mock.patch.object(web_app, "start_content_package_worker"):
                response = client.post("/api/content-studio/batch", json={"folder": str(root), "mode": "no_llm"})
            payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["count"], 1, payload)
        self.assertEqual(payload["skipped_count"], 2)
        self.assertEqual({item["reason"] for item in payload["skipped"]}, {"already_posted", "already_in_content_queue"})

    def test_content_batch_uses_confirmed_posts_when_legacy_ledger_is_behind(self):
        from web import app as web_app
        from src import content_packages

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "confirmed.mp4").write_bytes(b"video")
            (root / "unconfirmed.mp4").write_bytes(b"video")
            posts_file = root / "posts.json"
            posts_file.write_text(json.dumps([
                {"status": "published", "media_file": "confirmed.mp4", "post_fb_id": "video-123"},
                {"status": "scheduled", "media_file": "unconfirmed.mp4"},
            ]), encoding="utf-8")
            queue = root / "queue.json"
            with mock.patch.object(web_app, "BASE_DIR", root), mock.patch.object(
                web_app, "POSTS_FILE", posts_file
            ), mock.patch.object(content_packages, "QUEUE_FILE", queue), mock.patch.object(
                web_app, "get_clip_metadata", return_value={"video_title": "Test"}
            ), mock.patch.object(web_app, "start_content_package_worker"):
                response = web_app.app.test_client().post("/api/content-studio/batch", json={"folder": str(root), "mode": "no_llm"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["count"], 1)
        self.assertEqual(response.get_json()["skipped"][0]["reason"], "already_posted")

    def test_content_package_first_comment_receives_generated_website_url(self):
        from src import content_packages
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            queue_file = root / "content_packages.json"
            queue_file.write_text(json.dumps([{
                "id": "pkg-1", "clip_filename": "clip.mp4", "title": "Title", "summary": "Summary",
                "mode": "no_llm", "video_url": "", "create_website_article": True,
                "post_ids": [], "article_url": "", "status": "queued", "attempts": 0, "result": {}
            }]), encoding="utf-8")
            with mock.patch.object(content_packages, "QUEUE_FILE", queue_file), mock.patch.object(
                content_packages, "resolve_article_url", return_value=("https://example.test/article", "ready", "")
            ):
                content_packages.process_content_packages_once()
            item = json.loads(queue_file.read_text(encoding="utf-8"))[0]
        self.assertIn("https://example.test/article", item["result"]["first_comment"])
        self.assertEqual(item["website_status"], "ready")

    def test_package_failure_keeps_cms_and_content_errors_distinct_after_meta_success(self):
        from src import content_packages

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            posts_file = root / "posts.json"
            posts_file.write_text(json.dumps([{"id": "published-1", "status": "published",
                "post_fb_id": "meta-1", "website_status": "failed", "website_error": "CMS unavailable"}]), encoding="utf-8")
            with mock.patch.object(content_packages, "DATA_ROOT", root):
                content_packages._apply_failure_to_posts({"id": "package-1", "post_ids": ["published-1"],
                    "status": "failed", "website_status": "failed", "website_error": "CMS unavailable",
                    "error": "LLM generation failed"})
            saved = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        self.assertEqual(saved["status"], "published")
        self.assertEqual(saved["post_fb_id"], "meta-1")
        self.assertEqual(saved["website_error"], "CMS unavailable")
        self.assertEqual(saved["content_package_error"], "LLM generation failed")


class SchedulerWorkerHardeningTests(unittest.TestCase):
    def test_reel_without_website_link_never_reaches_meta(self):
        from web import scheduled_publisher as worker

        folder, root, output, posts_file = self._fixture({
            "id": "post-unlinked", "type": "reel", "status": "scheduled",
            "scheduled_time": "2026-01-01 00:00:00", "page_id": "page-1",
            "token": "fixture-token", "media_file": "clip.mp4",
            "first_comment": "Read more", "auto_first_comment": False,
        })
        poster = mock.Mock()
        try:
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "OUTPUT_DIR", output
            ), mock.patch.object(worker, "POSTED_CLIPS_FILE", root / "posted.json"):
                worker.process_scheduled_posts_once(poster=poster, now=datetime(2026, 1, 1, 1, 0, 0))
            saved = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        finally:
            folder.cleanup()
        self.assertEqual(saved["status"], "scheduled")
        self.assertEqual(saved["retry_stage"], "website_content")
        poster.publish_reel.assert_not_called()

    def _fixture(self, post):
        folder = tempfile.TemporaryDirectory()
        root = Path(folder.name)
        output = root / "output"
        output.mkdir()
        (output / "clip.mp4").write_bytes(b"video")
        posts_file = root / "posts.json"
        posts_file.write_text(json.dumps([post]), encoding="utf-8")
        return folder, root, output, posts_file

    def test_processing_post_id_persists_and_only_read_only_verification_updates_ledger(self):
        from src.publisher import first_comment_queue
        from src.publisher.meta_reel_poster import MetaReelPoster
        from web import scheduled_publisher as worker

        folder, root, output, posts_file = self._fixture({
            "id": "post-pending", "status": "scheduled", "scheduled_time": "2026-01-01 00:00:00",
            "page_id": "page-1", "token_id": "tok-1", "media_file": "clip.mp4",
        })
        poster = mock.Mock()
        poster.publish_reel.return_value = {"success": False, "processing": True,
            "meta_post_id": "123", "upload_video_id": "upload-1"}
        try:
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "OUTPUT_DIR", output
            ), mock.patch.object(worker, "POSTED_CLIPS_FILE", root / "posted.json"), mock.patch.object(
                first_comment_queue, "QUEUE_FILE", root / "comments.json"
            ), mock.patch("src.publisher.meta_preflight.preflight_pages", return_value={
                "ok": True, "ready": [{"token": "verified-token", "token_id": "tok-1"}]
            }), mock.patch("src.publisher.page_manager.PageManager.list_pages", return_value=[{"page_id": "page-1"}]), mock.patch.object(
                MetaReelPoster, "check_processing_reel", side_effect=[{"verified": False}, {"verified": False},
                    {"verified": True, "video_id": "upload-1", "fb_url": "https://www.facebook.com/reel/upload-1/"}]
            ) as check:
                worker.process_scheduled_posts_once(poster=poster, now=datetime(2026, 1, 1, 1, 0, 0))
                pending = json.loads(posts_file.read_text(encoding="utf-8"))[0]
                self.assertEqual(pending["status"], "processing")
                self.assertEqual(pending["meta_post_id"], "123")
                self.assertFalse(pending["retryable"])
                self.assertFalse((root / "posted.json").exists())
                worker.process_scheduled_posts_once(poster=poster, now=datetime(2026, 1, 1, 1, 2, 0))
                self.assertEqual(json.loads(posts_file.read_text(encoding="utf-8"))[0]["status"], "processing")
                worker.process_scheduled_posts_once(poster=poster, now=datetime(2026, 1, 1, 1, 4, 0))
                confirmed = json.loads(posts_file.read_text(encoding="utf-8"))[0]
                self.assertEqual(confirmed["status"], "published")
                self.assertEqual(json.loads((root / "posted.json").read_text()), ["clip.mp4"])
                self.assertEqual(check.call_count, 3)
                self.assertEqual(confirmed["post_fb_id"], "upload-1")
                poster.publish_reel.assert_called_once()
                poster.post_first_comment.assert_not_called()
        finally:
            folder.cleanup()

    def test_confirmed_reel_remains_published_when_comment_and_ledger_fail(self):
        from src.publisher import first_comment_queue
        from web import scheduled_publisher as worker

        poster = mock.Mock()
        poster.publish_reel.return_value = {"success": True, "video_id": "video-confirmed"}
        poster.post_first_comment.side_effect = RuntimeError("comment unavailable")
        folder, root, output, posts_file = self._fixture({
            "id": "post-confirmed", "status": "scheduled", "scheduled_time": "2026-09-30 23:53:00",
            "page_id": "page-1", "token": "fixture-token", "media_file": "clip.mp4",
            "first_comment": "Read existing article", "website_status": "ready",
        })
        try:
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "OUTPUT_DIR", output
            ), mock.patch.object(first_comment_queue, "QUEUE_FILE", root / "comments.json"), mock.patch.object(
                worker, "_record_posted_clip", side_effect=OSError("ledger unavailable")
            ):
                result = worker.process_scheduled_posts_once(poster=poster, now=datetime(2026, 10, 1, 0, 9, 0))
                saved = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        finally:
            folder.cleanup()
        self.assertEqual(result["failed"], 0)
        self.assertEqual(saved["status"], "published")
        self.assertEqual(saved["post_fb_id"], "video-confirmed")
        self.assertFalse(saved["retryable"])
        self.assertEqual(saved["first_comment_status"], "pending_retry")
        self.assertIn("ledger unavailable", saved["ledger_error"])
        poster.publish_reel.assert_called_once()

    def test_worker_waits_for_content_package_before_meta_publish(self):
        from src.publisher import first_comment_queue
        from web import scheduled_publisher as worker

        poster = mock.Mock()
        poster.publish_reel.return_value = {"success": True, "video_id": "fixture-video"}
        folder, root, output, posts_file = self._fixture({
            "id": "post-package-running", "status": "scheduled",
            "scheduled_time": "2026-01-01 00:00:00", "page_id": "page-1",
            "token": "fixture-token", "media_file": "clip.mp4",
            "auto_first_comment": True, "content_package_status": "running",
        })
        try:
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "OUTPUT_DIR", output
            ), mock.patch.object(worker, "POSTED_CLIPS_FILE", root / "posted.json"), mock.patch.object(
                first_comment_queue, "QUEUE_FILE", root / "comments.json"
            ):
                result = worker.process_scheduled_posts_once(
                    poster=poster, now=datetime(2026, 1, 1, 1, 0, 0)
                )
                saved = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        finally:
            folder.cleanup()
        self.assertEqual(result["claimed"], 1)
        self.assertEqual(saved["status"], "scheduled")
        self.assertEqual(saved["content_package_status"], "running")
        poster.publish_reel.assert_not_called()
        poster.post_first_comment.assert_not_called()

    def test_due_post_missing_video_fails_before_meta_and_never_retries(self):
        from src.publisher import first_comment_queue
        from web import scheduled_publisher as worker

        folder, root, output, posts_file = self._fixture({
            "id": "missing-video", "status": "scheduled", "scheduled_time": "2026-01-01 00:00:00",
            "page_id": "page-1", "token": "fixture-token", "media_file": "gone.mp4",
            "auto_first_comment": True, "content_package_status": "queued",
        })
        poster = mock.Mock()
        try:
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "OUTPUT_DIR", output
            ), mock.patch.object(first_comment_queue, "QUEUE_FILE", root / "comments.json"):
                worker.process_scheduled_posts_once(poster=poster, now=datetime(2026, 1, 1, 1))
                worker.process_scheduled_posts_once(poster=poster, now=datetime(2026, 1, 1, 2))
                saved = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        finally:
            folder.cleanup()
        self.assertEqual(saved["status"], "failed")
        self.assertEqual(saved["retry_stage"], "local_video")
        self.assertEqual(saved["content_package_status"], "queued")
        poster.publish_reel.assert_not_called()

    def test_due_post_foreign_absolute_path_never_posts_same_named_output_clip(self):
        from src.publisher import first_comment_queue
        from web import scheduled_publisher as worker

        folder, root, output, posts_file = self._fixture({
            "id": "foreign-video", "status": "scheduled", "scheduled_time": "2026-01-01 00:00:00",
            "page_id": "page-1", "token": "fixture-token", "media_file": str(Path(tempfile.gettempdir()) / "clip.mp4"),
        })
        poster = mock.Mock()
        try:
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "OUTPUT_DIR", output
            ), mock.patch.object(first_comment_queue, "QUEUE_FILE", root / "comments.json"):
                worker.process_scheduled_posts_once(poster=poster, now=datetime(2026, 1, 1, 1))
                saved = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        finally:
            folder.cleanup()
        self.assertEqual(saved["status"], "failed")
        self.assertEqual(saved["retry_stage"], "local_video")
        poster.publish_reel.assert_not_called()

    def test_due_post_with_backlog_still_requires_exact_page_preflight(self):
        from src.publisher import first_comment_queue
        from web import scheduled_publisher as worker

        folder, root, output, posts_file = self._fixture({
            "id": "blocked-binding", "status": "scheduled", "scheduled_time": "2026-01-01 00:00:00",
            "page_id": "page-1", "token_id": "wrong-binding", "media_file": "clip.mp4",
            "auto_first_comment": True, "content_package_status": "running",
        })
        poster = mock.Mock()
        try:
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "OUTPUT_DIR", output
            ), mock.patch.object(first_comment_queue, "QUEUE_FILE", root / "comments.json"), mock.patch(
                "src.publisher.page_manager.PageManager.list_pages", return_value=[{"page_id": "page-1"}]
            ), mock.patch("src.publisher.meta_preflight.preflight_pages", return_value={
                "ok": False, "blocked": {"code": "wrong_token", "stage": "mapping", "action": "Sync Page"},
            }):
                worker.process_scheduled_posts_once(poster=poster, now=datetime(2026, 1, 1, 1))
                saved = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        finally:
            folder.cleanup()
        self.assertEqual(saved["status"], "failed")
        self.assertEqual(saved["retry_stage"], "meta_preflight")
        self.assertEqual(saved["content_package_status"], "running")
        poster.publish_reel.assert_not_called()

    def test_overdue_six_minutes_post_is_claimed_not_left_scheduled(self):
        """Field report: post due 12:25 still shown as scheduled at 12:31 (6 minutes late)."""
        from src.publisher import first_comment_queue
        from web import scheduled_publisher as worker

        class Poster:
            def publish_reel(self, **kwargs):
                return {"success": True, "video_id": "video-900"}

            def post_first_comment(self, *args, **kwargs):
                return {"success": True, "comment_id": "c-1"}

        folder, root, output, posts_file = self._fixture({
            "id": "post-late", "status": "scheduled", "scheduled_time": "2026-09-28 12:25:00",
            "page_id": "page-1", "token": "t", "media_file": "clip.mp4", "title": "T",
            "content": "C", "auto_first_comment": False, "first_comment": "Configured",
        })
        try:
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "POSTED_CLIPS_FILE", root / "posted.json"
            ), mock.patch.object(worker, "OUTPUT_DIR", output), mock.patch.object(
                first_comment_queue, "QUEUE_FILE", root / "queue.json"
            ):
                result = worker.process_scheduled_posts_once(
                    poster=Poster(), now=datetime(2026, 9, 28, 12, 31, 0)
                )
            persisted = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        finally:
            folder.cleanup()
        self.assertEqual(result["claimed"], 1)
        self.assertEqual(persisted["status"], "published")
        self.assertEqual(persisted["post_fb_id"], "video-900")

    def test_stuck_publishing_record_is_recovered_after_stale_claim(self):
        """Crash recovery: a killed cycle leaves status=publishing forever without reclaim."""
        from src.publisher import first_comment_queue
        from web import scheduled_publisher as worker

        class Poster:
            def publish_reel(self, **kwargs):
                return {"success": True, "video_id": "video-901"}

            def post_first_comment(self, *args, **kwargs):
                return {"success": True, "comment_id": "c-1"}

        folder, root, output, posts_file = self._fixture({
            "id": "post-stuck", "status": "publishing", "scheduled_time": "2026-09-28 10:00:00",
            "claimed_at": "2026-09-28 10:00:05", "page_id": "page-1", "token": "t",
            "media_file": "clip.mp4", "title": "T", "content": "C",
            "auto_first_comment": False, "first_comment": "Configured",
        })
        try:
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "POSTED_CLIPS_FILE", root / "posted.json"
            ), mock.patch.object(worker, "OUTPUT_DIR", output), mock.patch.object(
                first_comment_queue, "QUEUE_FILE", root / "queue.json"
            ):
                result = worker.process_scheduled_posts_once(
                    poster=Poster(), now=datetime(2026, 9, 28, 12, 30, 0)
                )
            persisted = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        finally:
            folder.cleanup()
        self.assertEqual(result["recovered"], 1)
        self.assertEqual(persisted["status"], "published")
        self.assertIn("claim_recovery", json.dumps(persisted))

    def test_ambiguous_publish_response_never_retries_or_marks_published(self):
        from src.publisher import first_comment_queue
        from web import scheduled_publisher as worker

        folder, root, output, posts_file = self._fixture({
            "id": "post-ambiguous", "status": "scheduled", "scheduled_time": "2026-01-01 00:00:00",
            "page_id": "page-1", "token": "fixture-token", "media_file": "clip.mp4", "auto_first_comment": False,
        })
        poster = mock.Mock()
        poster.publish_reel.return_value = {"success": False, "outcome_unknown": True, "error": "unknown outcome"}
        try:
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "OUTPUT_DIR", output
            ), mock.patch.object(worker, "POSTED_CLIPS_FILE", root / "posted.json"), mock.patch.object(
                first_comment_queue, "QUEUE_FILE", root / "comments.json"
            ), mock.patch("src.publisher.meta_preflight.preflight_pages", return_value={
                "ok": True, "ready": [{"token": "verified-page-token", "token_id": "tok_verified"}]
            }), mock.patch("src.publisher.page_manager.PageManager.list_pages", return_value=[{"page_id": "page-1"}]):
                worker.process_scheduled_posts_once(poster=poster, now=datetime(2026, 1, 1, 1, 0, 0))
                saved = json.loads(posts_file.read_text(encoding="utf-8"))[0]
                worker.process_scheduled_posts_once(poster=poster, now=datetime(2026, 1, 1, 2, 0, 0))
        finally:
            folder.cleanup()
        self.assertEqual(saved["status"], "failed")
        self.assertFalse(saved["retryable"])
        poster.publish_reel.assert_called_once()

    def test_fresh_publishing_claim_is_not_stolen(self):
        """A live in-flight claim inside the stale window must not be reclaimed twice."""
        from web import scheduled_publisher as worker

        folder, root, output, posts_file = self._fixture({
            "id": "post-live", "status": "publishing", "scheduled_time": "2026-09-28 12:29:00",
            "claimed_at": "2026-09-28 12:30:00", "media_file": "clip.mp4",
        })
        try:
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "OUTPUT_DIR", output
            ), mock.patch.object(worker, "POSTED_CLIPS_FILE", root / "posted.json"):
                result = worker.process_scheduled_posts_once(
                    poster=mock.Mock(), now=datetime(2026, 9, 28, 12, 30, 30)
                )
            persisted = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        finally:
            folder.cleanup()
        self.assertEqual(result["recovered"], 0)
        self.assertEqual(persisted["status"], "publishing")

    def test_stale_claim_after_publish_started_fails_closed_without_duplicate(self):
        """Unknown remote outcome must not be retried automatically after a crash."""
        from web import scheduled_publisher as worker

        poster = mock.Mock()
        folder, root, output, posts_file = self._fixture({
            "id": "post-unknown", "status": "publishing", "scheduled_time": "2026-09-28 10:00:00",
            "claimed_at": "2026-09-28 10:00:05", "publish_started_at": "2026-09-28 10:00:06",
            "page_id": "page-1", "token": "t", "media_file": "clip.mp4",
        })
        try:
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "OUTPUT_DIR", output
            ), mock.patch.object(worker, "POSTED_CLIPS_FILE", root / "posted.json"):
                result = worker.process_scheduled_posts_once(
                    poster=poster, now=datetime(2026, 9, 28, 12, 30, 0)
                )
            persisted = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        finally:
            folder.cleanup()
        self.assertEqual(result["recovered"], 1)
        self.assertEqual(persisted["status"], "failed")
        self.assertFalse(persisted["retryable"])
        self.assertEqual(persisted["retry_stage"], "publish_outcome_unknown")
        poster.publish_reel.assert_not_called()

    def test_corrupt_primary_recovers_from_backup_and_is_not_overwritten_empty(self):
        from web.posts_store import load_posts_file, save_posts_file

        with tempfile.TemporaryDirectory() as folder:
            posts_file = Path(folder) / "posts.json"
            original = [{"id": "keep-me", "status": "scheduled"}]
            save_posts_file(posts_file, original)
            save_posts_file(posts_file, original + [{"id": "newer", "status": "scheduled"}])
            posts_file.write_text("{malformed", encoding="utf-8")
            expected = original + [{"id": "newer", "status": "scheduled"}]
            recovered = load_posts_file(posts_file)
            persisted = json.loads(posts_file.read_text(encoding="utf-8"))
        self.assertEqual(recovered, expected)
        self.assertEqual(persisted, expected)

    def test_corrupt_primary_without_backup_raises_instead_of_returning_empty(self):
        from web.posts_store import PostsStoreError, load_posts_file

        with tempfile.TemporaryDirectory() as folder:
            posts_file = Path(folder) / "posts.json"
            posts_file.write_text("not-json", encoding="utf-8")
            with self.assertRaises(PostsStoreError):
                load_posts_file(posts_file)

    def test_publish_failure_is_explicit_failed_retryable(self):
        from src.publisher import first_comment_queue
        from web import scheduled_publisher as worker

        class Poster:
            def publish_reel(self, **kwargs):
                return {"success": False, "error": "mock publish rejected"}

        folder, root, output, posts_file = self._fixture({
            "id": "post-fail", "status": "scheduled", "scheduled_time": "2026-09-28 12:25:00",
            "page_id": "page-1", "token": "t", "media_file": "clip.mp4", "title": "T",
            "content": "C", "auto_first_comment": False, "first_comment": "",
        })
        try:
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "POSTED_CLIPS_FILE", root / "posted.json"
            ), mock.patch.object(worker, "OUTPUT_DIR", output), mock.patch.object(
                first_comment_queue, "QUEUE_FILE", root / "queue.json"
            ):
                result = worker.process_scheduled_posts_once(
                    poster=Poster(), now=datetime(2026, 9, 28, 12, 31, 0)
                )
            persisted = json.loads(posts_file.read_text(encoding="utf-8"))[0]
        finally:
            folder.cleanup()
        self.assertEqual(result["failed"], 1)
        self.assertEqual(persisted["status"], "failed")
        self.assertTrue(persisted["retryable"])
        self.assertEqual(persisted["retry_stage"], "facebook_publish")

    def test_naive_local_datetime_format_is_parsed_without_tz_error(self):
        """Stored timestamps are naive local strings; parsing must not require tzinfo."""
        from web.scheduled_publisher import _parse_scheduled_time

        self.assertEqual(
            _parse_scheduled_time("2026-09-28T12:25"),
            datetime(2026, 9, 28, 12, 25, 0),
        )
        self.assertEqual(
            _parse_scheduled_time("2026-09-28 12:25:30"),
            datetime(2026, 9, 28, 12, 25, 30),
        )
        self.assertIsNone(_parse_scheduled_time("not-a-date"))
        self.assertIsNone(_parse_scheduled_time(None))
        # Naive parsed value compares directly against naive local now().
        self.assertLess(_parse_scheduled_time("2020-01-01 00:00:00"), datetime.now())

    def test_worker_exception_records_failed_retryable_with_sanitized_error(self):
        """A raising cycle must be visible, retryable, and never leak tokens."""
        from web import scheduled_publisher as worker

        token = "EAAG-secret-token-value"
        with mock.patch.object(
            worker,
            "process_scheduled_posts_once",
            side_effect=RuntimeError(f"graph call failed page_token={token}"),
        ):
            original_process = worker.process_scheduled_posts_once
            worker.process_scheduled_posts_once = mock.Mock(
                side_effect=RuntimeError(f"graph call failed page_token={token}")
            )
            try:
                # Simulate one loop iteration body exactly as the loop does.
                try:
                    worker.process_scheduled_posts_once()
                    ok = True
                    err = None
                except Exception as exc:
                    ok = False
                    err = exc
                worker._touch_heartbeat(ok, err or "")
                status = worker.worker_status()
            finally:
                worker.process_scheduled_posts_once = original_process
        self.assertFalse(status["last_cycle_ok"])
        self.assertNotIn(token, status["last_error"])
        self.assertIn("graph call failed", status["last_error"])

    def test_worker_status_reports_heartbeat_fields(self):
        from web import scheduled_publisher as worker

        status = worker.worker_status()
        for key in ("running", "last_cycle_at", "last_cycle_ok", "last_error", "cycles", "thread_alive"):
            self.assertIn(key, status)
        self.assertIn("jitter_threshold_seconds", status)

    def test_scheduler_status_and_run_due_endpoints(self):
        from web import app as web_app

        web_app.app.config["TESTING"] = True
        folder, root, output, posts_file = self._fixture({
            "id": "post-api", "status": "scheduled", "scheduled_time": "2020-01-01 00:00:00",
            "page_id": "page-1", "page_name": "Page One", "token": "t",
            "media_file": "clip.mp4", "title": "T", "content": "C",
        })
        client = web_app.app.test_client()
        try:
            with mock.patch.object(web_app, "POSTS_FILE", posts_file), mock.patch.object(
                web_app, "OUTPUT_DIR", output
            ):
                status_res = client.get("/api/scheduler/status")
                self.assertEqual(status_res.status_code, 200)
                payload = status_res.get_json()
                self.assertTrue(payload["success"])
                self.assertGreaterEqual(payload["overdue_count"], 1)
                self.assertEqual(payload["overdue_posts"][0]["id"], "post-api")
                self.assertGreaterEqual(payload["overdue_posts"][0]["late_seconds"], 300)

                with mock.patch(
                    "web.scheduled_publisher.process_scheduled_posts_once",
                    return_value={"claimed": 1, "recovered": 0, "failed": 0},
                ) as process:
                    run_res = client.post("/api/scheduler/run-due")
                self.assertEqual(run_res.status_code, 200)
                self.assertTrue(run_res.get_json()["success"])
                self.assertEqual(run_res.get_json()["claimed"], 1)
                process.assert_called_once_with()
        finally:
            folder.cleanup()

    def test_ui_has_worker_status_overdue_and_manual_trigger(self):
        root = Path(__file__).resolve().parent.parent
        html = (root / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn("/api/scheduler/status", html)
        self.assertIn("/api/scheduler/run-due", html)
        self.assertIn("scheduler-overdue-banner", html)
        self.assertIn("QUÁ HẠN", html)
        self.assertIn("startPostsAutoRefresh", html)
        self.assertIn("setInterval", html)

    def test_publishing_rows_are_not_marked_actionable_overdue(self):
        root = Path(__file__).resolve().parent.parent
        html = (root / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn("postsOverdueIds.has(p.id) && p.status === 'scheduled'", html)

    def test_publish_modal_dom_contract_exists_in_both_mirrors(self):
        root = Path(__file__).resolve().parent.parent
        for name in ("web/index.html", "web/templates/index.html"):
            html = (root / name).read_text(encoding="utf-8")
            for dom_id in ("modal-publish-reel", "pub-clip-title", "pub-clip-filename", "pub-select-single-page", "pub-select-group", "pub-caption", "pub-first-comment", "pub-schedule-datetime", "pub-schedule-stagger", "pub-status-banner", "btn-execute-publish"):
                self.assertIn(f'id="{dom_id}"', html)
            self.assertIn('onclick="executePublishReel()"', html)

    def test_start_worker_thread_is_idempotent(self):
        from web import scheduled_publisher as worker

        with mock.patch.object(worker, "scheduled_publisher_worker_loop", side_effect=lambda: None):
            first = worker.start_worker_thread()
            second = worker.start_worker_thread()
        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()
