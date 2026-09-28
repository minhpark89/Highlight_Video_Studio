import unittest
from unittest import mock


class YouTubeEmbedPublishTests(unittest.TestCase):
    def test_extract_youtube_id_supports_common_url_forms(self):
        from src.publisher.website_publisher import extract_youtube_video_id

        expected = "dQw4w9WgXcQ"
        self.assertEqual(extract_youtube_video_id(expected), expected)
        self.assertEqual(extract_youtube_video_id(f"https://youtu.be/{expected}?si=test"), expected)
        self.assertEqual(extract_youtube_video_id(f"https://www.youtube.com/watch?v={expected}&t=4"), expected)
        self.assertEqual(extract_youtube_video_id(f"https://www.youtube.com/shorts/{expected}"), expected)
        self.assertEqual(extract_youtube_video_id(f"https://www.youtube.com/embed/{expected}"), expected)
        self.assertEqual(extract_youtube_video_id("https://example.test/video"), "")

    def test_publish_uses_youtube_iframe_without_uploading_mp4(self):
        from src.publisher import website_publisher as publisher

        video_id = "dQw4w9WgXcQ"
        service = mock.Mock()
        service.publish_article.return_value = {
            "status": "success",
            "article_url": "https://example.test/blog/article",
        }
        with mock.patch.object(publisher, "get_website_config", return_value=(
            {"base_url": "https://example.test"}, mock.Mock(exists=mock.Mock(return_value=True))
        )), mock.patch.object(publisher, "get_clip_metadata", return_value={
            "video_title": "Fixture YouTube Story",
            "clean_title": "Fixture YouTube Story",
            "youtube_id": video_id,
            "youtube_url": f"https://youtu.be/{video_id}",
        }), mock.patch.object(
            publisher, "upload_long_video_to_public_stream"
        ) as upload, mock.patch.object(
            publisher, "extract_and_upload_article_assets", return_value=("https://img.test/hero.jpg", [])
        ), mock.patch.object(
            publisher, "get_llm_config", return_value={}
        ), mock.patch.object(
            publisher, "WebsiteArticleService", return_value=service
        ):
            article_url, _ = publisher.publish_clip_to_website_cms("clip.mp4")

        self.assertEqual(article_url, "https://example.test/blog/article")
        upload.assert_not_called()
        body_html = service.publish_article.call_args.kwargs["body_html"]
        self.assertIn(f"youtube-nocookie.com/embed/{video_id}", body_html)
        self.assertIn("<iframe", body_html)
        self.assertNotIn("<source src=", body_html)
        service.verify_article.assert_called_once_with(article_url)

    def test_publish_draft_youtube_embed_skips_video_upload(self):
        from web import app as web_app

        video_id = "dQw4w9WgXcQ"
        service = mock.Mock()
        service.publish_article.return_value = {
            "status": "success",
            "article_url": "https://example.test/blog/draft",
        }
        web_app.app.config["TESTING"] = True
        client = web_app.app.test_client()
        with mock.patch.object(web_app, "WebsiteArticleService", return_value=service), mock.patch.object(
            web_app, "generate_curiosity_comment_with_llm", return_value="Read the article"
        ):
            response = client.post("/api/website/publish_draft", json={
                "title": "Fixture Draft",
                "summary": "Fixture summary",
                "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                "video_path": "missing.mp4",
                "dry_run": True,
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["video_url"], f"https://www.youtube.com/watch?v={video_id}")
        service.upload_video.assert_not_called()
        service.verify_public_media.assert_not_called()
        body_html = service.publish_article.call_args.kwargs["body_html"]
        self.assertIn(f"youtube-nocookie.com/embed/{video_id}", body_html)
        self.assertNotIn("<video", body_html)


if __name__ == "__main__":
    unittest.main()
