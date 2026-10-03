import unittest

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


if __name__ == "__main__":
    unittest.main()
