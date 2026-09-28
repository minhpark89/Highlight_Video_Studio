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


if __name__ == "__main__":
    unittest.main()
