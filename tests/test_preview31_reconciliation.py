import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class Preview31ReconciliationTests(unittest.TestCase):
    def test_abandoned_worker_recovers_saved_article_without_republishing_unknown_cms(self):
        from src import content_packages as packages

        with tempfile.TemporaryDirectory() as folder:
            queue = Path(folder) / "packages.json"
            queue.write_text(json.dumps([
                {"id": "has-url", "status": "running", "article_url": "https://example.test/article",
                 "create_website_article": True},
                {"id": "unknown-cms", "status": "running", "article_url": "",
                 "create_website_article": True},
            ]), encoding="utf-8")
            with mock.patch.object(packages, "QUEUE_FILE", queue):
                self.assertTrue(packages.recover_abandoned_packages())
            rows = json.loads(queue.read_text(encoding="utf-8"))
            self.assertEqual(rows[0]["status"], "queued")
            self.assertEqual(rows[0]["article_url"], "https://example.test/article")
            self.assertEqual(rows[1]["status"], "failed")
            self.assertEqual(rows[1]["website_status"], "failed")

    def test_fallback_waiting_for_llm_is_visible_without_second_retry(self):
        from src import content_packages as packages

        with tempfile.TemporaryDirectory() as folder:
            queue = Path(folder) / "packages.json"
            item = {"id": "pending-1", "clip_filename": "clip.mp4", "status": "queued",
                    "article_url": "https://example.test/article", "website_status": "ready",
                    "result": {"caption": "Fallback caption", "source": "no_llm_error_fallback"}}
            queue.write_text(json.dumps([item]), encoding="utf-8")
            with mock.patch.object(packages, "QUEUE_FILE", queue):
                self.assertTrue(packages.package_needs_attention(item))
                self.assertEqual(packages.retry_package("pending-1")["status"], "queued")
                self.assertEqual(len(packages.list_packages()), 1)

    def test_schedule_attaches_existing_fallback_queue_without_new_package(self):
        from src import content_packages as packages

        with tempfile.TemporaryDirectory() as folder:
            queue = Path(folder) / "packages.json"
            queue.write_text(json.dumps([{
                "id": "pending-1", "clip_filename": str(Path(folder) / "clip.mp4"),
                "status": "queued", "post_ids": [], "article_url": "https://example.test/article",
                "website_status": "ready", "result": {"caption": "Fallback caption",
                "first_comment": "Read https://example.test/article", "source": "no_llm_error_fallback"},
            }]), encoding="utf-8")
            with mock.patch.object(packages, "QUEUE_FILE", queue), mock.patch.object(packages, "_apply_to_posts"):
                attached = packages.attach_existing_package(clip_filename="clip.mp4", post_ids=["post-1"])
            self.assertEqual(attached["id"], "pending-1")
            self.assertEqual(attached["status"], "queued")
            self.assertEqual(len(json.loads(queue.read_text(encoding="utf-8"))), 1)

    def test_ready_package_with_failed_website_is_visible_and_reused_without_new_row(self):
        from src import content_packages as packages

        with tempfile.TemporaryDirectory() as folder:
            queue = Path(folder) / "packages.json"
            queue.write_text(json.dumps([{
                "id": "library-1", "clip_filename": "clip.mp4", "status": "ready",
                "website_status": "failed", "website_error": "CMS rejected image",
                "create_website_article": True, "result": {"caption": "Existing caption", "article_html": "Existing article"},
            }]), encoding="utf-8")
            with mock.patch.object(packages, "QUEUE_FILE", queue), mock.patch.object(packages, "_apply_to_posts"):
                found = packages.attach_existing_package(clip_filename="clip.mp4", post_ids=["post-1"])
                self.assertTrue(packages.package_needs_attention(found))
            saved = json.loads(queue.read_text(encoding="utf-8"))
            self.assertEqual(len(saved), 1)
            self.assertEqual(found["status"], "ready")
            self.assertEqual(found["result"]["caption"], "Existing caption")
            self.assertEqual(found["website_status"], "failed")

    def test_retry_ready_website_failure_keeps_generated_text(self):
        from src import content_packages as packages

        with tempfile.TemporaryDirectory() as folder:
            queue = Path(folder) / "packages.json"
            queue.write_text(json.dumps([{
                "id": "library-1", "clip_filename": "clip.mp4", "title": "Title", "status": "ready",
                "website_status": "failed", "create_website_article": True,
                "result": {"caption": "Existing caption", "article_html": "Existing article", "source": "llm"},
            }]), encoding="utf-8")
            with mock.patch.object(packages, "QUEUE_FILE", queue), mock.patch.object(
                packages, "resolve_article_url", return_value=("https://example.test/article", "ready", "")
            ), mock.patch.object(packages, "generate_package") as generate, mock.patch.object(packages, "_apply_to_posts"):
                self.assertEqual(packages.retry_package("library-1")["status"], "queued")
                result = packages.process_content_packages_once()["item"]
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["result"]["caption"], "Existing caption")
            self.assertIn("https://example.test/article", result["result"]["first_comment"])
            generate.assert_not_called()

    def test_reel_check_requires_published_phase_and_accepts_relative_permalink(self):
        from src.publisher.meta_reel_poster import MetaReelPoster

        response = mock.Mock(ok=True, headers={}, json=lambda: {
            "id": "123", "status": {"video_status": "ready", "publishing_phase": {"publish_status": "processing"}},
            "permalink_url": "/reel/123/",
        })
        with mock.patch("src.publisher.meta_reel_poster.requests.get", return_value=response):
            self.assertFalse(MetaReelPoster().check_processing_reel("123", "token")["verified"])
            response.json = lambda: {"id": "123", "status": {
                "video_status": "ready", "publishing_phase": {"publish_status": "published"}},
                "permalink_url": "/reel/123/"}
            verified = MetaReelPoster().check_processing_reel("123", "token")
        self.assertEqual(verified["fb_url"], "https://www.facebook.com/reel/123/")


if __name__ == "__main__":
    unittest.main()
