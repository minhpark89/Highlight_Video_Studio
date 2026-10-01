"""Offline CMS article fallback and original-frame provenance checks."""
import re
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.publisher import website_publisher as p


class LongArticleFallbackTests(unittest.TestCase):
    def test_text_transport_requests_json_nonstream_and_rejects_partial_sse(self):
        response = mock.Mock(status_code=200)
        response.text = 'data: ' + json.dumps({"choices": [{"delta": {"content": "partial text"}}]}) + '\n'
        with mock.patch.object(p.requests, "post", return_value=response) as post:
            with self.assertRaisesRegex(RuntimeError, "stream ended without completion"):
                p._text_chat_request("https://llm.test/v1", "placeholder", "fixture", {"model": "fixture"}, 5)
        self.assertIs(post.call_args.kwargs["json"]["stream"], False)
        self.assertEqual(post.call_args.kwargs["headers"]["Accept"], "application/json")
        self.assertEqual(post.call_count, 1)

    def test_partial_http_200_sse_falls_back_for_article_and_comment(self):
        payload = {"lead_paragraph": "Invented outcome", "section_1_title": "Fake",
                   "section_1_content": "Unverified claim", "section_2_title": "Fake",
                   "section_2_content": "False details"}
        response = mock.Mock(status_code=200)
        response.text = 'data: ' + json.dumps({"choices": [{"delta": {"content": json.dumps(payload)}}]}) + '\n'
        with mock.patch.object(p, "get_llm_config", return_value={"api_base": "https://llm.test/v1", "api_key": "placeholder", "model": "fixture"}), mock.patch.object(
            p.requests, "post", return_value=response
        ) as post:
            _, body = p.generate_deep_article_content("Fixture", "", [], youtube_id="abcdefghijk")
            comment = p.generate_curiosity_comment_with_llm("Fixture", "https://cms.test/article")
        self.assertIn("How to examine the original sequence", body)
        self.assertNotIn("Invented outcome", body)
        self.assertNotIn("Invented outcome", comment)
        self.assertIn("https://cms.test/article", comment)
        self.assertEqual(post.call_count, 2)
        self.assertTrue(all(call.kwargs["json"]["stream"] is False for call in post.call_args_list))

    def test_fake_youtube_host_cannot_authorize_embed_or_thumbnail(self):
        self.assertEqual(p.extract_youtube_video_id("https://notyoutube.test/watch?v=abcdefghijk"), "")
        self.assertEqual(p.extract_youtube_video_id("https://youtube.com.evil.test/watch?v=abcdefghijk"), "")

    def test_missing_text_llm_produces_long_grounded_copy_with_original_embed(self):
        with mock.patch.object(p, "get_llm_config", return_value={}):
            _, body = p.generate_deep_article_content(
                "Fixture title", "https://cdn.test/source.jpg", ["https://cdn.test/source.jpg"],
                youtube_id="abcdefghijk")
        plain = re.sub(r"<[^>]*>", " ", body)
        self.assertGreaterEqual(len(re.findall(r"\b[A-Za-z]+\b", plain)), 500)
        self.assertIn("How to examine the original sequence", body)
        self.assertIn("What the footage can and cannot confirm", body)
        self.assertIn("youtube-nocookie.com/embed/abcdefghijk", body)
        self.assertNotIn("tactical genius", body.lower())

    def test_short_llm_article_is_replaced_whole_not_mixed_with_fallback(self):
        response = mock.Mock(status_code=200)
        with mock.patch.object(p, "get_llm_config", return_value={"api_base": "https://llm.test/v1", "api_key": "fixture", "model": "fixture"}), mock.patch.object(
            p, "_text_chat_request", return_value=response
        ), mock.patch.object(p, "json_from_chat_response", return_value={
            "lead_paragraph": "Invented spectator reaction", "section_1_title": "Short",
            "section_1_content": "Invented outcome", "section_2_title": "Aftermath", "section_2_content": "Invented expert quote",
        }):
            _, body = p.generate_deep_article_content("Fixture", "", [], youtube_id="abcdefghijk")
        self.assertNotIn("Invented", body)
        self.assertIn("How to examine the original sequence", body)

    def test_portrait_original_rejected_even_when_crop_would_be_horizontal(self):
        capture = mock.Mock()
        capture.isOpened.return_value = True
        capture.get.side_effect = [720, 1280]
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(p, "HAS_CV2", True), mock.patch.object(
            p.cv2, "VideoCapture", return_value=capture
        ):
            source = Path(folder) / "original.mp4"
            source.write_bytes(b"fixture")
            self.assertEqual(p.select_smart_video_frame(str(source)), "")
        capture.read.assert_not_called()
        capture.release.assert_called_once()

    @unittest.skipUnless(p.HAS_CV2, "OpenCV unavailable")
    def test_synthetic_landscape_original_yields_real_wide_frame(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "original.avi"
            frame = Path(folder) / "frame.jpg"
            writer = p.cv2.VideoWriter(str(source), p.cv2.VideoWriter_fourcc(*"MJPG"), 2, (320, 180))
            self.assertTrue(writer.isOpened())
            for index in range(8):
                image = np.full((180, 320, 3), 40 + index * 15, dtype=np.uint8)
                p.cv2.rectangle(image, (30, 25), (220, 125), (220, 90, 40), 3)
                writer.write(image)
            writer.release()
            result = p.select_smart_video_frame(str(source), output_path=str(frame))
            self.assertEqual(result, str(frame))
            self.assertTrue(p._valid_image_file(result, landscape=True))

    def test_cms_receives_long_fallback_and_verified_source_frame_without_network(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "original.mp4"
            source.write_bytes(b"fake source video")
            frame = root / "wide.jpg"
            frame.write_bytes(b"fixture landscape pixels" * 40)
            config = root / "cms.json"
            config.write_text("{}", encoding="utf-8")
            svc = mock.Mock()
            svc._presign_and_upload.return_value = "https://cdn.test/source.jpg"
            svc.publish_article.return_value = {"status": "success", "article_url": "https://cms.test/article"}
            metadata = {"video_title": "Fixture original video", "youtube_url": "https://youtu.be/abcdefghijk", "source_video_path": str(source)}
            with mock.patch.object(p, "HVS_DIR", root), mock.patch.object(p, "get_website_config", return_value=({}, config)), mock.patch.object(
                p, "get_clip_metadata", return_value=metadata
            ), mock.patch.object(p, "get_image_provider_config", return_value={"model": "__video_frame__"}), mock.patch.object(
                p, "get_llm_config", return_value={}
            ), mock.patch.object(p, "WebsiteArticleService", return_value=svc), mock.patch.object(
                p, "_BackendSession"
            ), mock.patch.object(p, "select_smart_video_frame", return_value=str(frame)) as select, mock.patch.object(
                p, "_valid_image_file", return_value=True
            ), mock.patch.object(p, "upload_long_video_to_public_stream") as video_upload:
                url, hero = p.publish_clip_to_website_cms("portrait.mp4")
            self.assertEqual((url, hero), ("https://cms.test/article", "https://cdn.test/source.jpg"))
            self.assertEqual(select.call_count, 2)
            self.assertTrue(all(call.args[0] == str(source) for call in select.call_args_list))
            self.assertEqual(svc._presign_and_upload.call_count, 2)
            video_upload.assert_not_called()
            body = svc.publish_article.call_args.kwargs["body_html"]
            self.assertGreaterEqual(len(re.findall(r"\b[A-Za-z]+\b", re.sub(r"<[^>]*>", " ", body))), 500)
            self.assertIn("youtube-nocookie.com/embed/abcdefghijk", body)
            self.assertEqual(svc.publish_article.call_args.kwargs["image_url"], hero)

    def test_no_verified_video_fails_before_assets_or_cms(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "cms.json"
            config.write_text("{}", encoding="utf-8")
            with mock.patch.object(p, "get_website_config", return_value=({}, config)), mock.patch.object(
                p, "get_clip_metadata", return_value={"video_title": "Fixture title"}
            ), mock.patch.object(p, "extract_and_upload_article_assets") as assets, mock.patch.object(
                p, "WebsiteArticleService"
            ) as service:
                with self.assertRaises(p.WebsiteServiceError):
                    p.publish_clip_to_website_cms("portrait.mp4")
            assets.assert_not_called()
            service.assert_not_called()


if __name__ == "__main__":
    unittest.main()
