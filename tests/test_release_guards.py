import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from core.website_article_service import WebsiteArticleService, WebsiteServiceError


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text="", url="https://example.test/item"):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.url = url
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        return self._payload


class ReleaseGuardTests(unittest.TestCase):
    def make_service(self, folder, video_upload=None):
        key = Path(folder) / "key"
        key.write_text("test", encoding="utf-8")
        config = Path(folder) / "website.json"
        config.write_text(json.dumps({
            "base_url": "https://example.test",
            "username": "admin",
            "password": "secret",
            "video_upload": video_upload or {
                "method": "scp", "host": "video.test", "port": 22,
                "username": "deploy", "private_key_path": str(key),
                "remote_dir": "/srv/videos", "public_base_url": "https://cdn.test/videos",
            },
        }), encoding="utf-8")
        return WebsiteArticleService(str(config))

    def test_scp_failure_never_returns_fabricated_url(self):
        with tempfile.TemporaryDirectory() as folder:
            service = self.make_service(folder)
            video = Path(folder) / "video.mp4"
            video.write_bytes(b"video")
            failed = mock.Mock(returncode=1, stderr="permission denied", stdout="")
            with mock.patch("core.website_article_service.shutil.which", return_value="scp.exe"), mock.patch(
                "core.website_article_service.subprocess.run", return_value=failed
            ):
                with self.assertRaisesRegex(WebsiteServiceError, "permission denied"):
                    service.upload_video(str(video))

    def test_scp_uses_argument_list_and_verifies_range(self):
        with tempfile.TemporaryDirectory() as folder:
            service = self.make_service(folder)
            video = Path(folder) / "my video.mp4"
            video.write_bytes(b"video")
            success = mock.Mock(returncode=0, stderr="", stdout="")
            with mock.patch("core.website_article_service.shutil.which", return_value="scp.exe"), mock.patch(
                "core.website_article_service.subprocess.run", return_value=success
            ) as run, mock.patch.object(service, "verify_public_media") as verify:
                public_url = service.upload_video(str(video))
            command = run.call_args.args[0]
            self.assertIsInstance(command, list)
            self.assertIn("BatchMode=yes", command)
            self.assertTrue(public_url.startswith("https://cdn.test/videos/my-video-"))
            verify.assert_called_once_with(public_url, require_range=True)

    @mock.patch("core.website_article_service.time.sleep", return_value=None)
    @mock.patch("core.website_article_service.requests.get")
    def test_article_redirect_to_home_is_rejected(self, get, _sleep):
        with tempfile.TemporaryDirectory() as folder:
            service = self.make_service(folder)
            get.return_value = FakeResponse(status_code=200, url="https://example.test/")
            with self.assertRaisesRegex(WebsiteServiceError, "Không xác minh"):
                service.verify_article("https://example.test/blog/wanted", attempts=2)

    def test_llm_list_and_chat_probe_are_independent(self):
        from web.app import app
        app.config["TESTING"] = True
        client = app.test_client()
        listed = FakeResponse(200, {"data": [{"id": "model-a"}]})
        rejected = FakeResponse(404, {"error": {"message": "No active credentials"}}, "")
        with mock.patch("web.app.requests.get", return_value=listed):
            result = client.post("/api/llm/models", json={"api_base": "https://router.test/v1", "api_key": "k"})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.get_json()["models"], ["model-a"])
        with mock.patch("web.app.requests.post", return_value=rejected):
            result = client.post("/api/llm/test", json={
                "api_base": "https://router.test/v1", "api_key": "k", "model": "model-a"
            })
            self.assertEqual(result.status_code, 502)
            self.assertIn("No active credentials", result.get_json()["error"])

    def test_first_comment_queue_survives_and_retries(self):
        from src.publisher import first_comment_queue as queue
        with tempfile.TemporaryDirectory() as folder:
            queue_file = Path(folder) / "queue.json"
            poster = mock.Mock()
            poster.post_first_comment.return_value = {"success": False, "error": "temporary"}
            with mock.patch.object(queue, "QUEUE_FILE", queue_file):
                queue.enqueue_first_comment("object", "token", "comment", 100)
                queue.process_due_first_comments(poster, now=100)
                persisted = json.loads(queue_file.read_text(encoding="utf-8"))
            self.assertEqual(persisted[0]["attempts"], 1)
            self.assertEqual(persisted[0]["status"], "pending")
            self.assertEqual(persisted[0]["due_at"], 130)

    def test_concurrent_job_updates_use_unique_atomic_files(self):
        from web import app as web_app
        with tempfile.TemporaryDirectory() as folder:
            jobs_file = Path(folder) / "jobs.json"
            with mock.patch.object(web_app, "JOBS_FILE", jobs_file):
                self.assertTrue(web_app.save_jobs([{"id": f"job-{i}", "step": 0} for i in range(20)]))
                threads = [
                    threading.Thread(target=web_app.update_job_status, args=(f"job-{i}", {"step": i + 1}))
                    for i in range(20)
                ]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
                saved = json.loads(jobs_file.read_text(encoding="utf-8"))
                leftovers = list(Path(folder).glob("*.tmp"))
            self.assertEqual([job["step"] for job in saved], list(range(1, 21)))
            self.assertEqual(leftovers, [])

    def test_task_specific_models_fall_back_to_main_model(self):
        from src.publisher.website_publisher import get_task_model
        config = {"model": "main", "task_models": {"article": "writer", "image": "__video_frame__"}}
        self.assertEqual(get_task_model("article", config), "writer")
        self.assertEqual(get_task_model("first_comment", config), "main")
        self.assertEqual(get_task_model("image", config), "__video_frame__")

    def test_public_config_never_returns_llm_api_key(self):
        from web.app import public_config
        original = {"llm": {"api_key": "super-secret", "model": "writer"}}
        safe = public_config(original)
        self.assertNotIn("api_key", safe["llm"])
        self.assertTrue(safe["llm"]["has_api_key"])
        self.assertEqual(original["llm"]["api_key"], "super-secret")

    def test_job_pipeline_resolves_all_lazy_pipeline_functions(self):
        from web import app as web_app
        with tempfile.TemporaryDirectory() as folder:
            rendered = Path(folder) / "clip.mp4"
            rendered.write_bytes(b"video")
            downloader = mock.Mock(return_value={
                "video_path": Path(folder) / "source.mp4",
                "audio_path": Path(folder) / "audio.wav",
                "title": "Test title",
                "duration": 60,
            })
            transcript = mock.Mock(return_value=[{"start": 0, "duration": 20, "text": "hello"}])
            whisper = mock.Mock(return_value=[])
            highlights = mock.Mock(return_value=[{"start": 0, "end": 20, "title": "Hook"}])
            renderer = mock.Mock(return_value=rendered)
            extractor = mock.Mock(return_value="video-id")
            updates = []
            with mock.patch.object(web_app, "get_pipeline_tools", return_value=(
                downloader, transcript, whisper, highlights, renderer, extractor
            )), mock.patch.object(web_app, "update_job_status", side_effect=lambda job_id, data: updates.append(data)):
                web_app.run_job_pipeline({"id": "job-test", "youtube_url": "https://youtu.be/test", "num_clips": 1})
            downloader.assert_called_once()
            transcript.assert_called_once_with("video-id")
            renderer.assert_called_once()
            self.assertEqual(updates[-1]["status"], "completed")

    def test_ytdlp_json3_captions_are_available_without_whisper(self):
        from src.pipeline import _parse_ytdlp_json3
        with tempfile.TemporaryDirectory() as folder:
            caption_file = Path(folder) / "captions.json3"
            caption_file.write_text(json.dumps({"events": [
                {"tStartMs": 1250, "dDurationMs": 2500, "segs": [
                    {"utf8": "hello"}, {"utf8": " world"}
                ]},
                {"tStartMs": 3750, "dDurationMs": 100, "segs": [{"utf8": "\n"}]},
            ]}), encoding="utf-8")
            items = _parse_ytdlp_json3(caption_file)
        self.assertEqual(items, [{
            "start": 1.25,
            "duration": 2.5,
            "text": "hello world",
        }])


if __name__ == "__main__":
    unittest.main()
