"""Offline regression for original-long-video image provenance."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class ImageSourceTests(unittest.TestCase):
    def test_non_llm_article_is_substantial_grounded_and_uses_original_horizontal_images(self):
        import re
        from src.publisher import website_publisher as publisher

        with mock.patch.object(publisher, "get_llm_config", return_value={}):
            _, body = publisher.generate_deep_article_content(
                "Fixture title", "https://cdn.test/original-wide.jpg",
                ["https://cdn.test/original-wide.jpg", "https://cdn.test/original-wide-2.jpg"],
                youtube_id="abcdefghijk",
            )
        words = re.findall(r"\b[A-Za-z]+\b", re.sub(r"<[^>]*>", " ", body))
        self.assertGreaterEqual(len(words), 290)
        self.assertIn("How to examine the original sequence", body)
        self.assertIn("What the footage can and cannot confirm", body)
        self.assertIn("original-wide-2.jpg", body)
        self.assertIn("youtube-nocookie.com/embed/abcdefghijk", body)
        self.assertNotIn("viewers witnessed", body)
        self.assertNotIn("tactical genius", body.lower())

    def test_content_package_fallback_is_grounded_and_escapes_untrusted_metadata(self):
        import re
        from src.content_packages import fallback_package

        result = fallback_package("<script>Sample</script>")
        plain = re.sub(r"<[^>]*>", " ", result["article_html"])
        self.assertGreaterEqual(len(re.findall(r"\b[A-Za-z]+\b", plain)), 280)
        self.assertIn("&lt;script&gt;", result["article_html"])
        self.assertNotIn("<script>", result["article_html"])
        self.assertNotIn("viewers are replaying", plain.lower())

    def test_article_401_at_v1_chat_completions_uses_grounded_long_fallback(self):
        import re
        from src.publisher import website_publisher as publisher

        with mock.patch.object(publisher, "get_llm_config", return_value={
            "api_base": "http://example.test:20128/v1/", "model": "fixture-model", "api_key": "fixture-key"
        }), mock.patch.object(publisher, "requests") as requests_mock:
            requests_mock.post.return_value.status_code = 401
            _, body = publisher.generate_deep_article_content(
                "Fixture title", "", [], youtube_id="abcdefghijk"
            )
            self.assertEqual(requests_mock.post.call_args.args[0], "http://example.test:20128/v1/chat/completions")
        plain = re.sub(r"<[^>]*>", " ", body)
        self.assertGreaterEqual(len(re.findall(r"\b[A-Za-z]+\b", plain)), 290)
        self.assertIn("How to examine the original sequence", body)

    def test_frame_mode_uses_original_video_not_short_clip(self):
        from src.publisher import website_publisher as publisher

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "long.mp4"
            source.write_bytes(b"original video")
            cfg = root / "website.json"
            cfg.write_text("{}", encoding="utf-8")
            uploaded = []

            with mock.patch.object(publisher, "HVS_DIR", root), mock.patch.object(
                publisher, "get_website_config", return_value=({}, cfg)
            ), mock.patch.object(publisher, "WebsiteArticleService") as service, mock.patch.object(
                publisher, "_BackendSession"
            ), mock.patch.object(publisher, "get_clip_metadata", return_value={"source_video_path": str(source), "clip_start": 10, "clip_end": 20}), mock.patch.object(publisher, "get_image_provider_config", return_value={"model": "__video_frame__"}), mock.patch.object(
                publisher, "generate_llm_hook_image"
            ) as generate, mock.patch.object(
                publisher, "select_smart_video_frame", side_effect=lambda path, *args: str(root / "wide.jpg")
            ) as select:
                service.return_value._presign_and_upload.side_effect = lambda _session, path: uploaded.append(path) or f"https://cdn.test/{Path(path).name}"
                hero, body = publisher.extract_and_upload_article_assets("portrait-clip.mp4", "Story")
            self.assertEqual(select.call_count, 2)
            self.assertTrue(all(call.args[0] == str(source) for call in select.call_args_list))
            self.assertTrue(hero.startswith("https://cdn.test/"))
            self.assertEqual(len(body), 2)
            self.assertEqual(len(uploaded), 2)
            generate.assert_not_called()

    def test_missing_local_long_video_uses_original_youtube_thumbnail(self):
        from src.publisher import website_publisher as publisher

        with tempfile.TemporaryDirectory() as folder:
            cfg = Path(folder) / "website.json"
            cfg.write_text("{}", encoding="utf-8")
            with mock.patch.object(publisher, "get_website_config", return_value=({}, cfg)), mock.patch.object(
                publisher, "get_clip_metadata", return_value={"youtube_url": "https://youtube.com/watch?v=abcdefghijk"}
            ), mock.patch.object(publisher, "WebsiteArticleService"), mock.patch.object(
                publisher, "_BackendSession"
            ), mock.patch.object(publisher, "get_image_provider_config", return_value={"model": "__video_frame__"}), mock.patch.object(
                publisher, "select_smart_video_frame"
            ) as select:
                hero, body = publisher.extract_and_upload_article_assets("portrait-clip.mp4", "Story")
        self.assertEqual(hero, "https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg")
        self.assertEqual(body, [hero])
        select.assert_not_called()


if __name__ == "__main__":
    unittest.main()
