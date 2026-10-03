import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from multi_pc.json_io import replace_with_retry
from src.publisher.meta_reel_poster import MetaReelPoster
from web.posts_store import load_posts_file, save_posts_file


class RuntimeRepairTests(unittest.TestCase):
    def test_replace_retries_windows_sharing_violation(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "new.json"
            target = Path(folder) / "ledger.json"
            source.write_text("[1]", encoding="utf-8")
            target.write_text("[]", encoding="utf-8")
            attempts = 0
            real_replace = os.replace

            def busy_twice(a, b):
                nonlocal attempts
                attempts += 1
                if attempts <= 2:
                    raise PermissionError(5, "sharing violation")
                return real_replace(a, b)

            with mock.patch("multi_pc.json_io.os.replace", side_effect=busy_twice):
                replace_with_retry(source, target, timeout=2)
            self.assertEqual(attempts, 3)
            self.assertEqual(target.read_text(encoding="utf-8"), "[1]")

    def test_meta_error_keeps_diagnostic_fields(self):
        message = MetaReelPoster._meta_error({"error": {
            "message": "Permission denied", "code": 200,
            "error_subcode": 123, "fbtrace_id": "trace-abc",
        }})
        for field in ("Permission denied", "code: 200", "subcode: 123", "trace: trace-abc"):
            self.assertIn(field, message)

    def test_stale_queue_revision_preserves_independent_publish(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "posts.json"
            save_posts_file(path, [{"id": "a", "status": "scheduled"}])
            stale = load_posts_file(path)
            save_posts_file(path, [{"id": "a", "status": "published", "post_fb_id": "fb-1"}])
            stale[0]["content_package_status"] = "ready"
            save_posts_file(path, stale)
            rows = load_posts_file(path)
            self.assertEqual(rows[0]["status"], "published")
            self.assertEqual(rows[0]["post_fb_id"], "fb-1")
            self.assertEqual(rows[0]["content_package_status"], "ready")

    def test_stale_queue_revision_does_not_delete_new_post(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "posts.json"
            save_posts_file(path, [{"id": "a", "status": "scheduled"}])
            stale = load_posts_file(path)
            save_posts_file(path, [{"id": "a", "status": "scheduled"}, {"id": "b", "status": "scheduled"}])
            stale[0]["content"] = "generated"
            save_posts_file(path, stale)
            rows = load_posts_file(path)
            self.assertEqual({row["id"] for row in rows}, {"a", "b"})
