import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class ContentStudioPrompt22Tests(unittest.TestCase):
    def test_ready_package_is_reused_for_same_clip_basename(self):
        from src import content_packages

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            queue = root / "content_packages.json"
            queue.write_text(json.dumps([{
                "id": "library-1",
                "clip_filename": str(root / "library" / "clip.mp4"),
                "status": "ready",
                "website_status": "ready",
                "article_url": "https://example.test/article",
                "result": {"caption": "Existing caption", "first_comment": "Read https://example.test/article", "source": "no_llm"},
                "post_ids": [],
            }]), encoding="utf-8")
            with mock.patch.object(content_packages, "QUEUE_FILE", queue), mock.patch.object(content_packages, "_apply_to_posts"):
                found = content_packages.attach_existing_package(clip_filename="clip.mp4", post_ids=["post-1"])
            self.assertEqual(found["id"], "library-1")
            self.assertEqual(found["post_ids"], ["post-1"])

    def test_failed_package_retry_moves_to_queue_without_generating_in_request(self):
        from src import content_packages

        with tempfile.TemporaryDirectory() as folder:
            queue = Path(folder) / "content_packages.json"
            queue.write_text(json.dumps([{"id": "pkg-1", "status": "failed", "error": "CMS down"}]), encoding="utf-8")
            with mock.patch.object(content_packages, "QUEUE_FILE", queue):
                item = content_packages.retry_package("pkg-1")
            self.assertEqual(item["status"], "queued")
            self.assertEqual(item["error"], "")

    def test_failed_queue_endpoint_supports_package_retry(self):
        from web import app as web_app
        from src import content_packages

        web_app.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as folder:
            queue = Path(folder) / "content_packages.json"
            queue.write_text(json.dumps([{"id": "pkg-1", "title": "Fixture", "status": "failed", "error": "CMS down"}]), encoding="utf-8")
            client = web_app.app.test_client()
            with mock.patch.object(content_packages, "QUEUE_FILE", queue), mock.patch.object(web_app, "start_content_package_worker") as worker:
                response = client.post("/api/content-studio/retry", json={"id": "pkg-1"})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.get_json()["queued"])
            worker.assert_called_once()

    def test_both_content_studio_templates_have_failed_filter_and_feedback(self):
        base = Path(__file__).resolve().parent.parent
        for relative in ("web/index.html", "web/templates/index.html"):
            html = (base / relative).read_text(encoding="utf-8")
            self.assertIn('id="cs-status-filter"', html)
            self.assertIn("csRetryPackage", html)
            self.assertIn('id="cs-action-msg"', html)
            self.assertIn("aria-busy", html)
            self.assertIn("fallback_reason", html)
            self.assertIn("Cần bài CMS có URL trước khi tạo comment", html)


if __name__ == "__main__":
    unittest.main()
