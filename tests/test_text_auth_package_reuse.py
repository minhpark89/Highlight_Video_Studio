"""Offline auth and Content Studio reuse regressions; no live CMS or Meta calls."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class TextAuthReuseTests(unittest.TestCase):
    def test_chat_url_and_diagnostic_never_include_provider_body(self):
        from src.text_llm_diagnostics import chat_endpoint, chat_failure
        self.assertEqual(chat_endpoint("http://example.test:20128/v1/"),
                         "http://example.test:20128/v1/chat/completions")
        self.assertEqual(chat_endpoint("http://example.test:20128"),
                         "http://example.test:20128/v1/chat/completions")
        self.assertIn("credential missing", chat_failure(401, has_key=False, has_model=True))
        self.assertIn("credential rejected", chat_failure(401, has_key=True, has_model=True))
        self.assertIn("model missing", chat_failure(401, has_key=True, has_model=False))
        with self.assertRaises(ValueError):
            chat_endpoint("http://user:private@example.test/v1")

    def test_package_401_is_explicit_and_secret_safe(self):
        from src import content_packages as cp
        cfg = {"configured_base": "http://example.test:20128/v1/", "api_key": "fixture-private", "model": "text-model"}
        with mock.patch("src.content_builder.get_llm_candidates", return_value=cfg), mock.patch(
            "src.content_builder._get_task_model", return_value="text-model"
        ), mock.patch.object(cp.requests, "post") as post, mock.patch.object(cp, "circuit_status", return_value={"open": False}):
            post.return_value.status_code = 401
            post.return_value.text = "fixture-private provider diagnostic"
            result = cp.generate_package("Fixture")
            self.assertEqual(post.call_args.args[0], "http://example.test:20128/v1/chat/completions")
            self.assertEqual(result["source"], "no_llm_error_fallback")
            self.assertIn("credential rejected", result["fallback_reason"])
            self.assertNotIn("fixture-private", result["fallback_reason"])

    def test_viral_content_401_does_not_return_short_template(self):
        from src import content_builder as builder
        cfg = {"configured_base": "http://example.test:20128/v1", "api_key": "fixture-private", "model": "text-model"}
        with mock.patch.object(builder, "get_llm_candidates", return_value=cfg), mock.patch.object(
            builder, "_get_task_model", return_value="text-model"
        ), mock.patch.object(builder.requests, "post") as post:
            post.return_value.status_code = 401
            post.return_value.text = "fixture-private"
            with self.assertRaisesRegex(RuntimeError, "credential rejected") as raised:
                builder.generate_viral_content("Fixture")
            self.assertNotIn("fixture-private", str(raised.exception))

    def test_attach_ready_package_preserves_article_and_post_content(self):
        from src import content_packages as cp
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            queue = root / "queue.json"
            posts = root / "posts.json"
            url = "https://example.test/article"
            queue.write_text(json.dumps([{"id": "pkg-ready", "clip_filename": str(root / "clip.mp4"),
                "source_job_id": "job-one", "source_clip_id": "1", "status": "ready", "website_status": "ready",
                "article_url": url, "post_ids": [], "result": {"caption": "Library caption", "hero_title": "Library title",
                "first_comment": "Read " + url, "source": "llm"}}]), encoding="utf-8")
            posts.write_text(json.dumps([{"id": "post-one", "status": "scheduled", "media_file": "clip.mp4"}]), encoding="utf-8")
            with mock.patch.object(cp, "QUEUE_FILE", queue), mock.patch.object(cp, "DATA_ROOT", root):
                reused = cp.attach_existing_package(clip_filename="clip.mp4", post_ids=["post-one"],
                    source_job_id="job-one", source_clip_id="1")
                self.assertIsNone(cp.attach_existing_package(clip_filename="clip.mp4", post_ids=["other"],
                    source_job_id="job-other", source_clip_id="1"))
            updated = json.loads(posts.read_text(encoding="utf-8"))[0]
            self.assertEqual(reused["id"], "pkg-ready")
            self.assertEqual(updated["content"], "Library caption")
            self.assertEqual(updated["article_url"], url)
            self.assertEqual(updated["first_comment"], "Read " + url)
            self.assertEqual(len(json.loads(queue.read_text(encoding="utf-8"))), 1)

    def test_worker_reuses_existing_ready_without_cms(self):
        from src import content_packages as cp
        with tempfile.TemporaryDirectory() as folder:
            queue = Path(folder) / "queue.json"
            url = "https://example.test/article"
            ready = {"id": "ready", "clip_filename": "clip.mp4", "status": "ready", "website_status": "ready",
                     "article_url": url, "result": {"caption": "Existing", "first_comment": "Read " + url}}
            queued = {"id": "new", "clip_filename": "clip.mp4", "status": "queued", "title": "New", "post_ids": [],
                      "article_url": "", "create_website_article": True}
            queue.write_text(json.dumps([ready, queued]), encoding="utf-8")
            with mock.patch.object(cp, "QUEUE_FILE", queue), mock.patch.object(cp, "resolve_article_url") as cms:
                processed = cp.process_content_packages_once()["item"]
            cms.assert_not_called()
            self.assertEqual(processed["article_url"], url)
            self.assertEqual(processed["result"]["caption"], "Existing")


if __name__ == "__main__":
    unittest.main()
