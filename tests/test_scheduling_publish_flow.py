import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock


class SchedulingPublishFlowTests(unittest.TestCase):
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
        self.assertEqual(saved[0]["first_comment"], "Configured comment")
        self.assertEqual(saved[0]["first_comment_status"], "ready")
        self.assertEqual(saved[0]["article_url"], "https://example.test/article")
        self.assertEqual(saved[0]["website_status"], "ready")
        self.assertEqual(saved[0]["status"], "scheduled")
        self.assertEqual(saved[0]["token"], "page-token-verified")
        self.assertEqual(saved[0]["token_id"], "tok_verified")

    def test_batch_schedule_marks_generated_fields_pending_instead_of_missing(self):
        from web import app as web_app

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
            ):
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

    def test_worker_publishes_facebook_after_saved_website_failure(self):
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
        self.assertEqual(post["status"], "published")
        self.assertEqual(post["post_fb_id"], "video-website-failed")
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


class SchedulerWorkerHardeningTests(unittest.TestCase):
    def _fixture(self, post):
        folder = tempfile.TemporaryDirectory()
        root = Path(folder.name)
        output = root / "output"
        output.mkdir()
        (output / "clip.mp4").write_bytes(b"video")
        posts_file = root / "posts.json"
        posts_file.write_text(json.dumps([post]), encoding="utf-8")
        return folder, root, output, posts_file

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

    def test_start_worker_thread_is_idempotent(self):
        from web import scheduled_publisher as worker

        with mock.patch.object(worker, "scheduled_publisher_worker_loop", side_effect=lambda: None):
            first = worker.start_worker_thread()
            second = worker.start_worker_thread()
        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()
