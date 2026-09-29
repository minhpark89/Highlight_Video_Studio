import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import pipeline


class YouTubeCookieProfileTests(unittest.TestCase):
    def test_cookie_specs_point_to_existing_chrome_profile_not_user_data_root(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "Default" / "Network").mkdir(parents=True)
            (root / "Default" / "Network" / "Cookies").write_bytes(b"db")
            (root / "Profile 2").mkdir()
            (root / "Profile 2" / "Cookies").write_bytes(b"db")
            with mock.patch.object(pipeline, "CHROME_PROFILE_DIR", root):
                specs = pipeline._chrome_cookie_specs()
        self.assertEqual(specs, [f"chrome:{root / 'Default'}", f"chrome:{root / 'Profile 2'}"])
        self.assertNotIn(f"chrome:{root}", specs)

    def test_missing_profile_or_cookie_database_returns_no_browser_specs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "Default").mkdir()
            with mock.patch.object(pipeline, "CHROME_PROFILE_DIR", root):
                self.assertEqual(pipeline._chrome_cookie_specs(), [])
            with mock.patch.object(pipeline, "CHROME_PROFILE_DIR", root / "missing"):
                self.assertEqual(pipeline._chrome_cookie_specs(), [])


if __name__ == "__main__":
    unittest.main()
