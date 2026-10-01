import json
import os
import socket
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


class SchedulerReleaseFixTests(unittest.TestCase):
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
