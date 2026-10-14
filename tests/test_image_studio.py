"""Offline tests for Hermes Image Studio; no network calls or paid APIs."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / "hermes-image-studio.py"
spec = importlib.util.spec_from_file_location("hermes_image_studio_test", source)
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)


class ImageStudioTests(unittest.TestCase):
    def test_status_is_honest_when_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            result = studio.status()
        self.assertFalse(result["configured"])
        self.assertFalse(result["paid_fallback"])
        self.assertIn("não fará chamadas pagas", result["message"])

    def test_missing_provider_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(studio.ImageStudioError) as ctx:
                studio.generate("A photorealistic mountain landscape")
        self.assertEqual(ctx.exception.code, "provider_not_configured")
        self.assertEqual(ctx.exception.status, 503)

    def test_only_direct_https_hf_space_urls_are_allowed(self):
        cases = [
            "http://user-space.hf.space",
            "https://evil.example/image",
            "https://user-space.hf.space/path",
            "https://user:pass@user-space.hf.space",
            "https://user-space.hf.space:8443",
            "https://user-space.hf.space/?next=https://evil.example",
        ]
        for url in cases:
            with self.subTest(url=url), patch.dict(os.environ, {"HERMES_IMAGE_STUDIO_SPACE_URL": url}, clear=True):
                with self.assertRaises(studio.ImageStudioError):
                    studio.generate("A photorealistic mountain landscape")

    def test_prompt_and_aspect_validation_happens_before_network(self):
        with patch.dict(os.environ, {"HERMES_IMAGE_STUDIO_SPACE_URL": "https://my-space.hf.space"}, clear=True), \
             patch.object(studio, "_request") as request:
            for prompt, aspect in [("", "square"), ("ab", "square"), ("A valid prompt", "ultrawide")]:
                with self.assertRaises(studio.ImageStudioError):
                    studio.generate(prompt, aspect)
            request.assert_not_called()

    def test_possible_credentials_are_rejected(self):
        secret = "gsk_" + "x" * 30
        with patch.dict(os.environ, {"HERMES_IMAGE_STUDIO_SPACE_URL": "https://my-space.hf.space"}, clear=True), \
             patch.object(studio, "_request") as request:
            with self.assertRaises(studio.ImageStudioError) as ctx:
                studio.generate("Please draw this text " + secret)
            self.assertEqual(ctx.exception.code, "possible_secret")
            request.assert_not_called()

    def test_event_stream_parser_reads_json_data(self):
        result = studio._event_data(b'event: complete\ndata: [{"url":"/gradio_api/file=output.png"}]\n\n')
        self.assertEqual(result[0]["url"], "/gradio_api/file=output.png")

    def test_external_image_host_is_rejected(self):
        with self.assertRaises(studio.ImageStudioError) as ctx:
            studio._same_space_url("https://my-space.hf.space", "https://attacker.example/file.png")
        self.assertEqual(ctx.exception.code, "unsafe_provider_result")

    def test_successful_mock_generation_never_needs_paid_api(self):
        png = b"\x89PNG\r\n\x1a\n" + b"mock-image-data"
        responses = [
            (json.dumps({"event_id": "evt_123"}).encode(), "application/json"),
            (b'event: complete\ndata: [{"url":"/gradio_api/file=generated.png"}]\n\n', "text/event-stream"),
            (png, "image/png"),
        ]
        with patch.dict(os.environ, {"HERMES_IMAGE_STUDIO_SPACE_URL": "https://my-space.hf.space"}, clear=True), \
             patch.object(studio, "_request", side_effect=responses) as request:
            result = studio.generate("A cinematic mountain landscape at sunrise", "landscape")
        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "huggingface-zero-gpu-space")
        self.assertFalse(result["paid_fallback"])
        self.assertEqual(base64.b64decode(result["image_base64"]), png)
        self.assertEqual(request.call_count, 3)


if __name__ == "__main__":
    unittest.main()
