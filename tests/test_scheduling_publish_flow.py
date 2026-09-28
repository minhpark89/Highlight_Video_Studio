import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock


class SchedulingPublishFlowTests(unittest.TestCase):
    def test_schedule_payload_persists_comment_website_and_never_calls_meta(self):
        from web import app as web_app

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "output"
            output.mkdir()
            (output / "clip.mp4").write_bytes(b"video")
            posts_file = root / "posts.json"
            pages = [{"page_id": "page-1", "page_name": "Page One", "page_token": "fixture-token"}]
            client = web_app.app.test_client()
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app, "POSTS_FILE", posts_file
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
            pages = [{"page_id": "page-1", "page_name": "Page One", "page_token": "fixture-token"}]
            client = web_app.app.test_client()
            with mock.patch.object(web_app, "OUTPUT_DIR", output), mock.patch.object(
                web_app, "POSTS_FILE", posts_file
            ), mock.patch.object(web_app, "BASE_DIR", root), mock.patch.object(
                web_app.page_manager, "list_groups", return_value=groups
            ), mock.patch.object(web_app.page_manager, "list_pages", return_value=pages), mock.patch.object(
                web_app, "get_clip_metadata", return_value={"video_title": "Fixture title"}
            ):
                response = client.post("/api/distribute/batch", json={
                    "group_id": "group-1", "posts_per_page": 1, "auto_first_comment": True,
                })
            self.assertEqual(response.status_code, 200)
            saved = json.loads(posts_file.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["first_comment_status"], "pending_generation")
        self.assertEqual(saved[0]["website_status"], "pending_generation")
        self.assertEqual(saved[0]["first_comment"], "")

    def test_worker_publishes_before_comment_and_persists_urls(self):
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
            }]), encoding="utf-8")
            with mock.patch.object(worker, "POSTS_FILE", posts_file), mock.patch.object(
                worker, "POSTED_CLIPS_FILE", posted_file
            ), mock.patch.object(worker, "OUTPUT_DIR", output), mock.patch.object(
                first_comment_queue, "QUEUE_FILE", queue_file
            ):
                result = worker.process_scheduled_posts_once(
                    poster=Poster(),
                    now=datetime(2026, 1, 1, 1, 0, 0),
                    website_publisher=lambda filename, title: ("https://example.test/article", ""),
                    comment_generator=lambda title, url, enable_llm=True: f"Read: {url}",
                )
        post = result["posts"][0]
        self.assertEqual(calls[0], ("publish", ""))
        self.assertEqual(calls[1][0], "comment")
        self.assertEqual(post["status"], "published")
        self.assertEqual(post["article_url"], "https://example.test/article")
        self.assertEqual(post["fb_url"], "https://facebook.test/reel/123")
        self.assertEqual(post["first_comment_status"], "posted")

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


if __name__ == "__main__":
    unittest.main()
