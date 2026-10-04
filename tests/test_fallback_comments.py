import unittest
from unittest import mock

from src.content_packages import fallback_package
from src.fallback_comments import LEAD_INS, fallback_first_comment
from src.publisher.website_publisher import generate_curiosity_comment_with_llm


class FallbackCommentTests(unittest.TestCase):
    def test_varied_stable_comments_each_include_only_own_article_url(self):
        self.assertEqual(len(LEAD_INS), 30)
        comments = set()
        for index in range(100):
            url = f"https://example.test/blog/article-{index}"
            comment = fallback_first_comment(f"Video {index}", url)
            self.assertEqual(comment.count(url), 1)
            self.assertEqual(comment, fallback_first_comment(f"Video {index}", url))
            self.assertEqual(fallback_package(f"Video {index}", article_url=url)["first_comment"], comment)
            comments.add(comment.removesuffix(url).strip())
        self.assertGreaterEqual(len(comments), 25)

    def test_missing_or_invalid_article_never_gets_a_comment(self):
        for url in ("", "not-a-url", "javascript:alert(1)", "https://user:secret@example.test/a"):
            self.assertEqual(fallback_first_comment("Video", url), "")
            self.assertEqual(generate_curiosity_comment_with_llm("Video", url, enable_llm=False), "")

    def test_publisher_uses_same_fallback(self):
        url = "https://example.test/blog/one"
        self.assertEqual(generate_curiosity_comment_with_llm("Video", url, enable_llm=False),
                         fallback_first_comment("Video", url))

    def test_retired_task_model_uses_main_model_before_template(self):
        from src.publisher import website_publisher as publisher
        url = "https://example.test/blog/one"
        retired = mock.Mock(status_code=200)
        retired.json.return_value = {"choices": [{"message": {"content": "Gemini 3.5 Flash is no longer available. Please switch to Gemini 3.7 Flash."}}]}
        valid = mock.Mock(status_code=200)
        valid.json.return_value = {"choices": [{"message": {"content": "Watch the full recording: " + url}}]}
        cfg = {"api_base": "https://router.test/v1", "api_key": "fixture", "model": "working",
               "task_models": {"first_comment": "retired"}}
        with mock.patch.object(publisher, "get_llm_config", return_value=cfg), mock.patch.object(
            publisher, "_text_chat_request", side_effect=[retired, valid]
        ) as request:
            comment = publisher.generate_curiosity_comment_with_llm("Video", url)
        self.assertEqual(comment, "Watch the full recording: " + url)
        self.assertEqual([call.args[2] for call in request.call_args_list], ["retired", "working"])
        self.assertNotIn("no longer available", comment)

    def test_retired_main_model_returns_valid_template_not_provider_notice(self):
        from src.publisher import website_publisher as publisher
        url = "https://example.test/blog/one"
        retired = mock.Mock(status_code=200)
        retired.json.return_value = {"choices": [{"message": {"content": "Gemini 3.5 Flash is no longer available. Please switch to Gemini 3.7 Flash."}}]}
        with mock.patch.object(publisher, "get_llm_config", return_value={
            "api_base": "https://router.test/v1", "api_key": "fixture", "model": "retired"
        }), mock.patch.object(publisher, "_text_chat_request", return_value=retired) as request:
            comment = publisher.generate_curiosity_comment_with_llm("Video", url)
        self.assertEqual(comment, fallback_first_comment("Video", url))
        self.assertEqual(request.call_count, 1)


if __name__ == "__main__":
    unittest.main()
