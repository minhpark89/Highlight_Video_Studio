"""Regression guards for the Website/CMS settings UI in both shipped templates."""

import re
import unittest
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATHS = (
    BASE_DIR / "web" / "index.html",
    BASE_DIR / "web" / "templates" / "index.html",
)
WEBSITE_FUNCTIONS = (
    "loadWebsiteConfig",
    "updateVideoUploadAdvancedVisibility",
    "saveWebsiteConfig",
    "testWebsiteConnection",
    "testVideoUploader",
)


def function_body(source: str, name: str) -> str:
    match = re.search(rf"(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    if not match:
        raise AssertionError(f"Website UI function {name} is missing")
    start = match.end() - 1
    depth = 0
    quote = None
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ("'", '"', "`"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():index + 1]
    raise AssertionError(f"Website UI function {name} has no closing brace")


class WebsiteUiRegressionTests(unittest.TestCase):
    def test_both_templates_have_nav_pane_and_every_website_js_field(self):
        for path in TEMPLATE_PATHS:
            with self.subTest(template=path.relative_to(BASE_DIR)):
                html = path.read_text(encoding="utf-8")
                self.assertEqual(html.count('data-pane="pane-website"'), 1)
                self.assertEqual(html.count('id="pane-website"'), 1)
                self.assertIn(
                    "if (paneId === 'pane-website' && typeof loadWebsiteConfig === 'function') loadWebsiteConfig();",
                    html,
                )

                website_js = "\n".join(function_body(html, name) for name in WEBSITE_FUNCTIONS)
                js_field_ids = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", website_js))
                js_field_ids.update(re.findall(r"\b(cfg_(?:web|video)_[A-Za-z0-9_]+)\s*:", website_js))
                self.assertTrue(js_field_ids, "Expected Website/CMS JavaScript field references")

                html_ids = set(re.findall(r'\bid="([^"]+)"', html))
                missing = sorted(js_field_ids - html_ids)
                self.assertEqual(
                    missing,
                    [],
                    f"Website/CMS JavaScript references fields absent from {path.relative_to(BASE_DIR)}",
                )

    def test_source_and_runtime_templates_remain_identical(self):
        self.assertEqual(
            TEMPLATE_PATHS[0].read_bytes(),
            TEMPLATE_PATHS[1].read_bytes(),
            "web/index.html and web/templates/index.html must ship the same Website/CMS UI",
        )

    def test_inline_content_studio_renderer_closes_template_literal(self):
        for path in TEMPLATE_PATHS:
            with self.subTest(template=path.relative_to(BASE_DIR)):
                html = path.read_text(encoding="utf-8")
                self.assertRegex(
                    html,
                    r"</tr>`;\s*\}\)\.join\(''\);",
                    "Content Studio queue renderer must close its template literal before join()",
                )
                self.assertNotIn(
                    "</tr>      }).join('');",
                    html,
                    "Malformed renderer boundary would prevent all inline JavaScript from parsing",
                )

    def test_content_studio_retry_has_immediate_busy_feedback(self):
        for path in TEMPLATE_PATHS:
            with self.subTest(template=path.relative_to(BASE_DIR)):
                html = path.read_text(encoding="utf-8")
                self.assertIn("function csSetBusy(button, busy, label)", html)
                self.assertIn("aria-busy", html)
                self.assertIn("cs-spinner", html)
                self.assertIn(r"\u0110ang t\u1ea1o l\u1ea1i ti\u00eau \u0111\u1ec1...", html)
                self.assertIn(r"\u0110ang t\u1ea1o l\u1ea1i comment...", html)
                self.assertIn("create_website_article: true", html)

    def test_cms_is_default_and_scp_is_advanced_legacy_option(self):
        for path in TEMPLATE_PATHS:
            with self.subTest(template=path.relative_to(BASE_DIR)):
                html = path.read_text(encoding="utf-8")
                self.assertIn('<option value="cms" selected>Nhúng YouTube gốc + upload ảnh qua CMS (khuyên dùng)</option>', html)
                self.assertIn('<option value="scp">SCP/SSH lưu MP4 (nâng cao)</option>', html)
                self.assertIn('id="cfg_video_advanced" style="display:none', html)
                self.assertIn("advanced.style.display = method === 'scp' ? 'block' : 'none'", html)
                self.assertIn("cfg_video_method: video.method || 'cms'", html)

    def test_group_page_select_all_is_scoped_to_current_filter(self):
        for path in TEMPLATE_PATHS:
            with self.subTest(template=path.relative_to(BASE_DIR)):
                html = path.read_text(encoding="utf-8")
                self.assertIn('id="group-pages-filter"', html)
                self.assertIn('class="group-page-choice"', html)
                body = function_body(html, "setFilteredGroupPagesChecked")
                self.assertIn("getFilteredGroupPageChoices()", body)
                self.assertNotIn("querySelectorAll('.group-page-checkbox')", body)
                self.assertIn("setFilteredGroupPagesChecked(true)", html)
                self.assertIn("setFilteredGroupPagesChecked(false)", html)

    def test_failed_website_ui_offers_safe_manual_retry(self):
        for path in TEMPLATE_PATHS:
            with self.subTest(template=path.relative_to(BASE_DIR)):
                html = path.read_text(encoding="utf-8")
                self.assertIn("Thử lại Website", html)
                self.assertIn("/retry-website", html)
                self.assertIn("Lịch Facebook vẫn được giữ nguyên", html)


if __name__ == "__main__":
    unittest.main()
