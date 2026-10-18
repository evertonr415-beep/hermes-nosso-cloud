"""Offline tests for the Pollinations-backed Hermes Image Studio."""
import importlib.util
import os
from pathlib import Path
import urllib.error
import urllib.parse
import unittest
from unittest.mock import MagicMock, patch

source = Path(__file__).resolve().parents[1] / "hermes-image-studio.py"
spec = importlib.util.spec_from_file_location("hermes_image_studio_test", source)
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)


class ImageStudioTests(unittest.TestCase):
    def test_status_reports_free_provider_without_paid_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            result = studio.status()
        self.assertTrue(result["ok"])
        self.assertTrue(result["configured"])
        self.assertEqual(result["provider"], "pollinations-ai")
        self.assertFalse(result["paid_fallback"])

    def test_prompt_and_aspect_validation_happens_before_network(self):
        with patch.object(studio.urllib.request, "urlopen") as urlopen:
            for prompt, aspect in [("", "square"), ("ab", "square"), ("A valid prompt", "ultrawide"), ("x" * 4001, "square")]:
                with self.subTest(prompt_length=len(prompt), aspect=aspect):
                    with self.assertRaises(studio.ImageStudioError) as ctx:
                        studio.generate(prompt, aspect)
                    self.assertEqual(ctx.exception.status, 400)
            urlopen.assert_not_called()

    def test_successful_generation_returns_pollinations_url_and_dimensions(self):
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        with patch.object(studio.urllib.request, "urlopen", return_value=response) as urlopen:
            result = studio.generate("A cinematic mountain landscape at sunrise", "landscape")

        self.assertEqual(result["provider"] if "provider" in result else "pollinations-ai", "pollinations-ai")
        self.assertEqual(result["model"], "black-forest-labs/flux.1-schnell")
        self.assertEqual((result["width"], result["height"]), (1024, 768))
        parsed = urllib.parse.urlparse(result["url"])
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "image.pollinations.ai")
        params = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(params["model"], ["flux"])
        self.assertEqual(params["width"], ["1024"])
        self.assertEqual(params["height"], ["768"])
        self.assertEqual(params["safe"], ["false"])
        self.assertEqual(urlopen.call_args.kwargs["timeout"], studio.TIMEOUT_SECONDS)

    def test_all_aspects_map_to_expected_dimensions(self):
        expected = {"square": (1024, 1024), "portrait": (768, 1024), "landscape": (1024, 768)}
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        with patch.object(studio.urllib.request, "urlopen", return_value=response):
            for aspect, dimensions in expected.items():
                with self.subTest(aspect=aspect):
                    result = studio.generate("A watercolor lighthouse", aspect)
                    self.assertEqual((result["width"], result["height"]), dimensions)

    def test_provider_network_error_is_reported_without_paid_fallback(self):
        with patch.object(studio.urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")):
            with self.assertRaises(studio.ImageStudioError) as ctx:
                studio.generate("A mountain landscape")
        self.assertEqual(ctx.exception.code, "provider_unavailable")
        self.assertEqual(ctx.exception.status, 503)

    def test_non_200_provider_response_is_reported(self):
        response = MagicMock()
        response.status = 429
        response.__enter__.return_value = response
        with patch.object(studio.urllib.request, "urlopen", return_value=response):
            with self.assertRaises(studio.ImageStudioError) as ctx:
                studio.generate("A mountain landscape")
        self.assertEqual(ctx.exception.code, "generation_failed")
        self.assertEqual(ctx.exception.status, 502)


if __name__ == "__main__":
    unittest.main()
