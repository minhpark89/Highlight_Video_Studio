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

    def test_cms_video_upload_fails_before_auth_or_network_even_under_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            service = self.make_service(folder, {"method": "cms"})
            video = Path(folder) / "video.mp4"
            video.write_bytes(b"video")
            fake_session = mock.Mock()
            fake_session.authenticated = True
            with mock.patch("core.website_article_service._BackendSession", return_value=fake_session), mock.patch(
                "core.website_article_service.requests.request"
            ) as request:
                with self.assertRaisesRegex(WebsiteServiceError, "image-only.*5 MiB"):
                    service.upload_video(str(video))
                with self.assertRaisesRegex(WebsiteServiceError, "image-only"):
                    service.upload_public_media(str(video))
                with self.assertRaisesRegex(WebsiteServiceError, "image endpoint"):
                    service.test_video_uploader()
            fake_session.http.post.assert_not_called()
            request.assert_not_called()

    def test_cms_oversized_video_and_image_fail_without_presign(self):
        with tempfile.TemporaryDirectory() as folder:
            service = self.make_service(folder, {"method": "cms"})
            video = Path(folder) / "video.mp4"
            image = Path(folder) / "image.jpg"
            for path in (video, image):
                with path.open("wb") as handle:
                    handle.truncate(5 * 1024 * 1024 + 1)
            fake_session = mock.Mock()
            fake_session.authenticated = True
            with mock.patch("core.website_article_service._BackendSession", return_value=fake_session):
                with self.assertRaisesRegex(WebsiteServiceError, "exceeds the CMS 5 MiB image upload limit"):
                    service.upload_video(str(video))
                with self.assertRaisesRegex(WebsiteServiceError, "5 MiB"):
                    service.upload_public_media(str(image))
            fake_session.http.post.assert_not_called()

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

    def test_chat_probe_rejects_retired_model_notice_with_http_200(self):
        from web.app import app
        app.config["TESTING"] = True
        client = app.test_client()
        retired = FakeResponse(200, {"choices": [{"message": {
            "content": "Gemini 3.5 Flash is no longer available. Please switch to Gemini 3.7 Flash in the API."
        }}]})
        with mock.patch("web.app.requests.post", return_value=retired):
            response = client.post("/api/llm/test", json={
                "api_base": "https://router.test/v1", "api_key": "k", "model": "ag/gemini-3.5-flash-low"
            })
        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.get_json()["success"])
        self.assertIn("ngừng hoạt động", response.get_json()["error"])

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


    def test_public_config_never_returns_image_provider_api_key(self):
        from web.app import public_config
        original = {"image_provider": {"api_key": "image-secret", "model": "image-1"}}
        safe = public_config(original)
        self.assertNotIn("api_key", safe["image_provider"])
        self.assertTrue(safe["image_provider"]["has_api_key"])
        self.assertEqual(original["image_provider"]["api_key"], "image-secret")

    def test_image_provider_probe_uses_images_generations(self):
        from web.app import app
        app.config["TESTING"] = True
        client = app.test_client()
        generated = FakeResponse(200, {"data": [{"b64_json": "aW1hZ2U="}]})
        with mock.patch("web.app.requests.post", return_value=generated) as post:
            result = client.post("/api/image-provider/test", json={
                "api_base": "https://images.test/v1", "api_key": "k", "model": "image-1"
            })
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.get_json()["success"])
        self.assertEqual(post.call_args.args[0], "https://images.test/v1/images/generations")
        self.assertEqual(post.call_args.kwargs["json"], {
            "model": "image-1",
            "prompt": "A simple blue circle on white background",
            "n": 1,
            "size": "auto",
            "quality": "auto",
            "background": "auto",
            "image_detail": "high",
            "output_format": "png",
        })

    def test_image_model_listing_uses_independent_exact_url(self):
        from web.app import app
        app.config["TESTING"] = True
        client = app.test_client()
        listed = FakeResponse(200, {"data": [{"id": "image-model-a"}]})
        with mock.patch("web.app.requests.get", return_value=listed) as get:
            result = client.post("/api/image-provider/models", json={
                "models_url": "https://router.test/catalog/image-models", "api_key": "k"
            })
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.get_json()["models"], ["image-model-a"])
        self.assertEqual(get.call_args.args[0], "https://router.test/catalog/image-models")

    def test_image_generation_rejects_chat_endpoint_and_makes_no_request(self):
        from web.app import app
        app.config["TESTING"] = True
        client = app.test_client()
        with mock.patch("web.app.requests.post") as post:
            result = client.post("/api/image-provider/test", json={
                "generation_url": "https://router.test/v9/chat/completions",
                "models_url": "https://router.test/not-supported/models",
                "api_key": "k",
                "model": "image-model-a",
            })
        self.assertEqual(result.status_code, 400)
        self.assertIn("/v1/images/generations", result.get_json()["error"])
        post.assert_not_called()

    def test_runtime_image_config_preserves_explicit_frame_mode(self):
        from src.publisher import website_publisher as publisher
        root = {
            "image_provider": {
                "generation_url": "https://images.test/v1/images/generations",
                "models_url": "https://catalog.test/models",
                "model": "__video_frame__",
            },
            "llm": {"task_models": {"image": "real-image-model"}},
        }
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "config.json"
            config.write_text(json.dumps(root), encoding="utf-8")
            with mock.patch.object(publisher, "HVS_DIR", Path(folder)):
                resolved = publisher.get_image_provider_config()
        self.assertEqual(resolved["model"], "__video_frame__")
        self.assertEqual(resolved["generation_url"], "https://images.test/v1/images/generations")
        self.assertEqual(resolved["models_url"], "https://catalog.test/models")

    def test_runtime_image_response_extractor_accepts_url_base64_and_nested_chat(self):
        from src.publisher.website_publisher import _image_response_values
        fixtures = [
            ({"data": [{"url": "https://cdn.test/a.png"}]}, "https://cdn.test/a.png"),
            ({"data": [{"b64_json": "aW1hZ2U="}]}, "aW1hZ2U="),
            ({"choices": [{"message": {"images": [{"image_url": {"url": "https://cdn.test/b.png"}}]}}]}, "https://cdn.test/b.png"),
            ({"choices": [{"message": {"content": "data:image/png;base64,aW1hZ2U="}}]}, "aW1hZ2U="),
            ({"output": [{"content": "result: https://cdn.test/c.png"}]}, "https://cdn.test/c.png"),
        ]
        for payload, expected in fixtures:
            with self.subTest(payload=payload):
                self.assertIn(expected, _image_response_values(payload))

    def test_runtime_generation_uses_exact_images_endpoint_and_payload(self):
        from src.publisher import website_publisher as publisher
        encoded = "aW1hZ2U="
        generated = FakeResponse(200, {"data": [{"b64_json": encoded}]})
        config = {
            "image_provider": {
                "generation_url": "https://router.test/v1/images/generations",
                "models_url": "https://router.test/catalog/models",
                "api_key": "test-only-placeholder",
                "model": "ag/gemini-3.1-flash-image",
            }
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
            with mock.patch.object(publisher, "HVS_DIR", root), mock.patch(
                "src.publisher.website_publisher.requests.post", return_value=generated
            ) as post, mock.patch.object(publisher, "_valid_image_file", return_value=True):
                output = publisher.generate_llm_hook_image("Safe canary")
            self.assertTrue(Path(output).is_file())
            self.assertEqual(Path(output).read_bytes(), b"image")
        self.assertEqual(post.call_args.args[0], "https://router.test/v1/images/generations")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "ag/gemini-3.1-flash-image")
        self.assertEqual({k: payload[k] for k in ("n", "size", "quality", "background", "image_detail", "output_format")}, {
            "n": 1, "size": "auto", "quality": "auto", "background": "auto", "image_detail": "high", "output_format": "png",
        })

    def test_runtime_frame_mode_makes_no_external_request(self):
        from src.publisher import website_publisher as publisher
        config = {"image_provider": {"model": "__video_frame__", "generation_url": "https://router.test/v1/images/generations"}}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
            with mock.patch.object(publisher, "HVS_DIR", root), mock.patch("src.publisher.website_publisher.requests.post") as post:
                self.assertEqual(publisher.generate_llm_hook_image("Safe canary"), "")
        post.assert_not_called()

    def test_image_provider_accepts_nested_url_base64_and_content_outputs(self):
        from web.app import _image_response_has_output
        fixtures = [
            {"data": [{"url": "https://cdn.test/a.png"}]},
            {"data": [{"b64_json": "aW1hZ2U="}]},
            {"choices": [{"message": {"images": [{"image_url": {"url": "https://cdn.test/b.png"}}]}}]},
            {"choices": [{"message": {"content": "data:image/png;base64,aW1hZ2U="}}]},
            {"choices": [{"message": {"content": "result: https://cdn.test/c.png"}}]},
        ]
        for payload in fixtures:
            with self.subTest(payload=payload):
                self.assertTrue(_image_response_has_output(payload))

    def test_image_model_list_promotes_first_real_model_over_frame_sentinel(self):
        html = (Path(__file__).resolve().parent.parent / "web" / "templates" / "index.html").read_text(encoding="utf-8")
        start = html.index("async function checkImageEndpoint")
        end = html.index("async function testImageProvider", start)
        body = html[start:end]
        self.assertIn("data.models[0]", body)
        self.assertIn("__video_frame__", body)

    def test_source_and_packaged_templates_are_identical(self):
        root = Path(__file__).resolve().parent.parent
        self.assertEqual(
            (root / "web" / "templates" / "index.html").read_bytes(),
            (root / "web" / "index.html").read_bytes(),
        )

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

    def test_transcript_segments_generate_clip_relative_karaoke_words(self):
        from src.pipeline import transcript_segments_to_words
        words = transcript_segments_to_words([
            {"start": 9.0, "duration": 3.0, "text": "before clip starts"},
            {"start": 12.0, "duration": 2.0, "text": "viral subtitle"},
        ], clip_start=10.0, clip_duration=5.0)
        self.assertEqual([item["word"] for item in words], [
            "clip", "starts", "viral", "subtitle"
        ])
        self.assertGreaterEqual(words[0]["start"], 0.0)
        self.assertLessEqual(words[-1]["end"], 5.0)

    def test_fallback_highlights_always_match_requested_count(self):
        from src.pipeline import _fallback_highlights, _ensure_highlight_count
        transcript = [
            {"start": float(second), "duration": 5.0, "text": f"line {second}"}
            for second in range(0, 600, 10)
        ]
        fallback = _fallback_highlights(transcript, num_clips=3)
        self.assertEqual(len(fallback), 3)
        completed = _ensure_highlight_count(fallback[:2], transcript, num_clips=3)
        self.assertEqual(len(completed), 3)
        self.assertTrue(all(item["end"] > item["start"] for item in completed))


if __name__ == "__main__":
    unittest.main()
