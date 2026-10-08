import unittest
from unittest import mock


class YouTubeEmbedPublishTests(unittest.TestCase):
    def test_public_article_quality_requires_expected_images_and_summary(self):
        from core.website_article_service import WebsiteArticleService, WebsiteServiceError
        service = WebsiteArticleService.__new__(WebsiteArticleService)
        service.cfg = mock.Mock(timeout=3)
        article = ("<section><h2>Original video summary</h2><p>" + ("source context " * 620) + "</p>" +
                   "<img src='https://img.test/hero.jpg'><img src='https://img.test/one.jpg'>" +
                   "<img src='https://img.test/two.jpg'>Full Uncut Footage<iframe src='https://www.youtube-nocookie.com/embed/2GdRyatht4E'></iframe></section>")
        with mock.patch("core.website_article_service.requests.get", return_value=mock.Mock(
            status_code=200, url="https://example.test/blog/article", text=article
        )):
            result = service.verify_article_quality("https://example.test/blog/article",
                expected_images=["https://img.test/hero.jpg", "https://img.test/one.jpg", "https://img.test/two.jpg"])
            self.assertEqual(result["image_count"], 3)
            with self.assertRaises(WebsiteServiceError):
                service.verify_article_quality("https://example.test/blog/article",
                    expected_images=["https://img.test/missing.jpg"])

    def test_existing_cms_article_with_verified_embed_is_reused_without_post(self):
        from src.publisher import website_publisher as publisher

        video_id = "dQw4w9WgXcQ"
        def existing(url, **_kwargs):
            return mock.Mock(status_code=200, url=url,
                             text=f'<iframe src="https://www.youtube-nocookie.com/embed/{video_id}"></iframe>')
        with mock.patch.object(publisher, "get_website_config", return_value=(
            {"base_url": "https://example.test"}, mock.Mock(exists=mock.Mock(return_value=True))
        )), mock.patch.object(publisher, "get_clip_metadata", return_value={
            "video_title": "Fixture YouTube Story", "youtube_id": video_id,
        }), mock.patch.object(publisher.requests, "get", side_effect=existing), mock.patch.object(
            publisher, "extract_and_upload_article_assets"
        ) as assets, mock.patch.object(publisher, "WebsiteArticleService") as service:
            first = publisher.publish_clip_to_website_cms("clip.mp4")
            second = publisher.publish_clip_to_website_cms("clip.mp4")
        self.assertEqual(first, second)
        self.assertTrue(first[0].startswith("https://example.test/blog/"))
        assets.assert_not_called()
        self.assertEqual(service.call_count, 2)
        service.return_value.verify_article_english.assert_called()
        service.return_value.verify_article_embed.assert_called()
        service.return_value.verify_article_quality.assert_called()

    def test_extract_youtube_id_supports_common_url_forms(self):
        from src.publisher.website_publisher import extract_youtube_video_id

        expected = "dQw4w9WgXcQ"
        self.assertEqual(extract_youtube_video_id(expected), expected)
        self.assertEqual(extract_youtube_video_id(f"https://youtu.be/{expected}?si=test"), expected)
        self.assertEqual(extract_youtube_video_id(f"https://www.youtube.com/watch?v={expected}&t=4"), expected)
        self.assertEqual(extract_youtube_video_id(f"https://www.youtube.com/shorts/{expected}"), expected)
        self.assertEqual(extract_youtube_video_id(f"https://www.youtube.com/embed/{expected}"), expected)
        self.assertEqual(extract_youtube_video_id("https://example.test/video"), "")

    def test_saved_original_url_is_used_when_warehouse_clip_has_been_renamed(self):
        from src.publisher import website_publisher as publisher
        original = 'dQw4w9WgXcQ'
        receipt = {'video_url': f'https://youtu.be/{original}'}
        def existing(url, **kwargs):
            return mock.Mock(status_code=200, url=url, text=f'<iframe src="https://www.youtube-nocookie.com/embed/{original}"></iframe>')
        with mock.patch.object(publisher, 'get_website_config', return_value=(
            {'base_url':'https://example.test'}, mock.Mock(exists=mock.Mock(return_value=True))
        )), mock.patch.object(publisher, 'get_clip_metadata', return_value={'video_title':'Original cycling recording'}), \
                mock.patch.object(publisher.requests, 'get', side_effect=existing), \
                mock.patch.object(publisher, 'upload_long_video_to_public_stream') as upload, \
                mock.patch.object(publisher, 'WebsiteArticleService'):
            url, _ = publisher.publish_clip_to_website_cms('renamed.mp4', asset_metadata=receipt)
        upload.assert_not_called()
        self.assertTrue(url.startswith('https://example.test/blog/'))
        self.assertEqual(receipt['website_video_url'], f'https://www.youtube.com/watch?v={original}')

    @mock.patch("src.publisher.website_publisher.requests.get", return_value=mock.Mock(status_code=404))
    def test_publish_uses_youtube_iframe_without_uploading_mp4(self, _get):
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
            publisher, "extract_and_upload_article_assets", return_value=("https://img.test/hero.jpg", ["https://img.test/one.jpg", "https://img.test/two.jpg"])
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
        service.verify_article_embed.assert_called_once_with(
            article_url, youtube_id=video_id, video_stream_url=""
        )

    @mock.patch("src.publisher.website_publisher.requests.get", return_value=mock.Mock(status_code=404))
    def test_invalid_id_falls_back_to_original_youtube_url_before_upload(self, _get):
        from src.publisher import website_publisher as publisher

        video_id = "dQw4w9WgXcQ"
        service = mock.Mock()
        service.publish_article.return_value = {
            "status": "success", "article_url": "https://example.test/blog/article"
        }
        with mock.patch.object(publisher, "get_website_config", return_value=(
            {"base_url": "https://example.test"}, mock.Mock(exists=mock.Mock(return_value=True))
        )), mock.patch.object(publisher, "get_clip_metadata", return_value={
            "video_title": "Fixture Original Story", "youtube_id": "invalid",
            "youtube_url": f"https://youtu.be/{video_id}",
        }), mock.patch.object(publisher, "upload_long_video_to_public_stream") as upload, mock.patch.object(
            publisher, "extract_and_upload_article_assets", return_value=("https://img.test/hero.jpg", ["https://img.test/one.jpg", "https://img.test/two.jpg"])
        ), mock.patch.object(publisher, "get_llm_config", return_value={}), mock.patch.object(
            publisher, "WebsiteArticleService", return_value=service
        ):
            publisher.publish_clip_to_website_cms("clip.mp4")
        upload.assert_not_called()
        self.assertIn(f"youtube-nocookie.com/embed/{video_id}", service.publish_article.call_args.kwargs["body_html"])

    def test_no_youtube_and_rejected_video_stops_before_article_assets(self):
        from src.publisher import website_publisher as publisher
        from core.website_article_service import WebsiteServiceError

        with mock.patch.object(publisher, "get_website_config", return_value=(
            {"base_url": "https://example.test"}, mock.Mock(exists=mock.Mock(return_value=True))
        )), mock.patch.object(publisher, "get_clip_metadata", return_value={
            "video_title": "Fixture Original Story", "youtube_id": "invalid"
        }), mock.patch.object(publisher, "upload_long_video_to_public_stream", side_effect=WebsiteServiceError(
            "CMS video upload is not supported; 5 MiB image-only endpoint"
        )), mock.patch.object(publisher, "extract_and_upload_article_assets") as assets, mock.patch.object(
            publisher, "WebsiteArticleService"
        ) as service:
            with self.assertRaisesRegex(WebsiteServiceError, "5 MiB"):
                publisher.publish_clip_to_website_cms("clip.mp4")
        assets.assert_not_called()
        service.assert_not_called()

    @mock.patch("core.website_article_service.requests.get")
    def test_public_article_embed_verification_requires_original_marker(self, get):
        from core.website_article_service import WebsiteArticleService, WebsiteServiceError

        service = WebsiteArticleService.__new__(WebsiteArticleService)
        service.cfg = mock.Mock(timeout=3)
        get.return_value = mock.Mock(status_code=200, url="https://example.test/blog/new", text="<html>other video</html>")
        with self.assertRaises(WebsiteServiceError):
            service.verify_article_embed("https://example.test/blog/new", youtube_id="dQw4w9WgXcQ")
        get.return_value.text = '<iframe src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"></iframe>'
        self.assertEqual(
            service.verify_article_embed("https://example.test/blog/new", youtube_id="dQw4w9WgXcQ")["embed"],
            "youtube",
        )

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
