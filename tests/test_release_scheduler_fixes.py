import json
import os
import socket
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


class SchedulerReleaseFixTests(unittest.TestCase):
    def test_ready_website_package_queues_comment_for_already_published_reel(self):
        from src import content_packages
        from src.publisher import first_comment_queue
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            post_file = root / "posts.json"
            post_file.write_text(json.dumps([{
                "id": "post-1", "status": "published", "post_fb_id": "123456",
                "token": "fixture-token", "token_id": "token-1",
                "first_comment_status": "not_configured",
            }]), encoding="utf-8")
            queue_file = root / "comments.json"
            item = {
                "id": "package-1", "post_ids": ["post-1"], "status": "ready",
                "article_url": "https://example.test/article", "website_status": "ready",
                "result": {"caption": "Caption", "first_comment": "Read https://example.test/article"},
            }
            with mock.patch.object(content_packages, "DATA_ROOT", root), mock.patch.object(
                first_comment_queue, "QUEUE_FILE", queue_file
            ):
                content_packages._apply_to_posts(item)
                content_packages._apply_to_posts(item)
            comments = json.loads(queue_file.read_text(encoding="utf-8"))
            post = json.loads(post_file.read_text(encoding="utf-8"))[0]
            self.assertEqual(len(comments), 1)
            self.assertEqual(comments[0]["comment_text"], "Read https://example.test/article")
            self.assertEqual(post["first_comment_status"], "pending")

    def test_dead_local_lease_is_reclaimed_but_live_owner_is_preserved(self):
        from multi_pc.data_root import ProcessLease
        with tempfile.TemporaryDirectory() as folder:
            lease = ProcessLease("scheduler-test", Path(folder))
            lease.path.mkdir(parents=True)
            lease.owner_file.write_text(f"pid=99999999\nhost={socket.gethostname()}\n", encoding="utf-8")
            with mock.patch("multi_pc.data_root._local_pid_alive", return_value=False):
                self.assertTrue(lease.acquire())
            lease.release()
            lease.path.mkdir()
            lease.owner_file.write_text(f"pid={os.getpid()}\nhost={socket.gethostname()}\n", encoding="utf-8")
            os.utime(lease.path, (time.time() - 3600, time.time() - 3600))
            with mock.patch("multi_pc.data_root._local_pid_alive", return_value=True):
                self.assertFalse(lease.acquire())
            self.assertTrue(lease.owner_file.exists())

    def test_cleanup_waits_for_every_page_and_resolves_path_aliases(self):
        from web import scheduled_publisher as worker
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "output"
            output.mkdir()
            clip = output / "clip.mp4"
            clip.write_bytes(b"video")
            ledger = Path(folder) / "posted_clips.json"
            ledger.write_text(json.dumps(["clip.mp4"]), encoding="utf-8")
            posts = [
                {"media_file": "clip.mp4", "status": "published", "post_fb_id": "123"},
                {"media_file": str(clip), "status": "scheduled", "post_fb_id": ""},
            ]
            with mock.patch.object(worker, "OUTPUT_DIR", output), mock.patch.object(worker, "POSTED_CLIPS_FILE", ledger):
                self.assertFalse(worker.remove_posted_clip_file("clip.mp4", posts))
                self.assertTrue(clip.exists())
                posts[1].update(status="published", post_fb_id="456")
                self.assertTrue(worker.remove_posted_clip_file("clip.mp4", posts))
                self.assertFalse(clip.exists())


if __name__ == "__main__":
    unittest.main()
