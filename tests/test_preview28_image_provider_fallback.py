"""Offline, credential-free tests for image-provider failures and fallback."""
import logging
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

from src.publisher import website_publisher as publisher


class ImageProviderFallbackTests(unittest.TestCase):
    def run_image(self, response=None, side_effect=None):
        cfg = {
            "api_base": "",
            "generation_url": "https://images.test/v1/images/generations",
            "api_key": "test-placeholder",
            "model": "ag/gemini-3.1-flash-image",
        }
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            publisher, "HVS_DIR", Path(folder)
        ), mock.patch.object(publisher, "get_image_provider_config", return_value=cfg), mock.patch.object(
            publisher.requests, "post", return_value=response, side_effect=side_effect
        ) as post, self.assertLogs("website_publisher", level="WARNING") as captured:
            result = publisher.generate_llm_hook_image("Safe canary")
            files = list((Path(folder) / "temp").iterdir())
        return result, files, post, "\n".join(captured.output)

    def test_gateway_502_is_not_retried_or_mislabeled_client(self):
        response = mock.Mock(status_code=502)
        result, files, post, logs = self.run_image(response=response)
        self.assertEqual(result, "")
        self.assertEqual(files, [])
        post.assert_called_once()
        self.assertIn("upstream/gateway HTTP 502", logs)
        self.assertNotIn("test-placeholder", logs)
        self.assertNotIn("images.test", logs)
        self.assertFalse(response.json.called)

    def test_401_is_client_config_and_never_retried(self):
        response = mock.Mock(status_code=401)
        result, _, post, logs = self.run_image(response=response)
        self.assertEqual(result, "")
        post.assert_called_once()
        self.assertIn("client/config HTTP 401", logs)
        self.assertFalse(response.json.called)

    def test_transport_exception_does_not_log_url_or_secret(self):
        error = requests.ConnectionError("https://images.test/secret-placeholder")
        result, _, post, logs = self.run_image(side_effect=error)
        self.assertEqual(result, "")
        post.assert_called_once()
        self.assertIn("ConnectionError", logs)
        self.assertNotIn("secret-placeholder", logs)
        self.assertNotIn("images.test", logs)

    def test_http_200_invalid_json_uses_fallback(self):
        response = mock.Mock(status_code=200)
        response.json.side_effect = ValueError("secret-placeholder")
        result, files, post, logs = self.run_image(response=response)
        self.assertEqual(result, "")
        self.assertEqual(files, [])
        post.assert_called_once()
        self.assertIn("invalid JSON", logs)
        self.assertNotIn("secret-placeholder", logs)

    def test_http_200_without_image_uses_fallback(self):
        response = mock.Mock(status_code=200)
        response.json.return_value = {"data": []}
        result, _, post, logs = self.run_image(response=response)
        self.assertEqual(result, "")
        post.assert_called_once()
        self.assertIn("no usable landscape image", logs)


if __name__ == "__main__":
    unittest.main()
