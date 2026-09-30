"""Offline regression for original-long-video image provenance."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class ImageSourceTests(unittest.TestCase):
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
