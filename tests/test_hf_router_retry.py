"""Offline regression tests: Hugging Face live model discovery and guarded failover."""
import importlib.util
import json
import os
import pathlib
import unittest
import urllib.error
from unittest.mock import patch

ROUTER = pathlib.Path(__file__).resolve().parent.parent / "hermes-global-model-router.py"
spec = importlib.util.spec_from_file_location("hermes_router_test", ROUTER)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)

ENV = {
    "HF_TOKEN": "hf_" + "x" * 29,
    "HERMES_GLOBAL_ROUTER_ENABLED": "1",
    "HERMES_GLOBAL_PROVIDERS_JSON": "[]",
    "HERMES_GLOBAL_KEYLESS_ALLOW": "0",
}


class FakeResponse:
    def __init__(self, body=None):
        self.body = body if body is not None else {
            "choices": [{"message": {"content": "OK"}}]
        }

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, *args):
        return json.dumps(self.body).encode()


LIVE = {
    "Qwen/Qwen3-4B-Instruct-2507": ["nscale", "featherless-ai"],
    "Qwen/Qwen2.5-7B-Instruct-1M": ["featherless-ai"],
}


class HuggingFaceRouterTests(unittest.TestCase):
    def setUp(self):
        router._MODEL_CACHE.update(until=0.0, models=None)

    def call(self):
        return router.run({
            "prompt": "Olá",
            "provider_id": "huggingface-official",
            "sensitivity": "normal",
            "max_tokens": 16,
        })

    def test_model_catalog_parser_requires_live_provider(self):
        parsed = router.parse_live_models({
            "data": [
                {"id": "Qwen/Qwen3-4B-Instruct-2507",
                 "providers": [{"provider": "nscale", "status": "live"}]},
                {"id": "Qwen/Qwen2.5-7B-Instruct",
                 "providers": [{"provider": "together", "status": "error"}]},
                {"id": "random/untrusted", "providers": [{"provider": "x", "status": "live"}]},
            ]
        })
        self.assertEqual(parsed, {"Qwen/Qwen3-4B-Instruct-2507": ["nscale"]})

    def test_default_prefers_qwen3(self):
        with patch.dict(os.environ, ENV, clear=True):
            self.assertEqual(router.configured()[0]["model"],
                             "Qwen/Qwen3-4B-Instruct-2507")

    def test_unavailable_configured_model_selects_live_qwen(self):
        with (
            patch.dict(os.environ, {**ENV, "HERMES_HF_MODEL": "Qwen/Qwen2.5-7B-Instruct"}),
            patch.object(router, "discover_hf_models", return_value=LIVE),
            patch.object(router.urllib.request, "urlopen", return_value=FakeResponse()) as hit,
        ):
            response = self.call()
        self.assertTrue(response["ok"])
        self.assertEqual(response["model"], "Qwen/Qwen3-4B-Instruct-2507:nscale")
        self.assertEqual(hit.call_count, 1)

    def test_404_tries_one_alternate_live_model(self):
        unavailable = urllib.error.HTTPError("https://router.huggingface.co", 404, "model", None, None)
        with (
            patch.dict(os.environ, ENV, clear=True),
            patch.object(router, "discover_hf_models", return_value=LIVE),
            patch.object(router.urllib.request, "urlopen", side_effect=[unavailable, FakeResponse()]) as hit,
        ):
            response = self.call()
        self.assertTrue(response["ok"])
        self.assertEqual(response["model"], "Qwen/Qwen2.5-7B-Instruct-1M")
        self.assertEqual(hit.call_count, 2)

    def test_transient_503_retries_once_then_succeeds(self):
        unavailable = urllib.error.HTTPError("https://router.huggingface.co", 503, "temp", None, None)
        with (
            patch.dict(os.environ, ENV, clear=True),
            patch.object(router, "discover_hf_models", return_value=LIVE),
            patch.object(router.urllib.request, "urlopen", side_effect=[unavailable, FakeResponse()]) as hit,
            patch.object(router.time, "sleep"),
        ):
            response = self.call()
        self.assertTrue(response["ok"])
        self.assertEqual(response["attempts"], 2)
        self.assertEqual(hit.call_count, 2)

    def test_402_never_retries_or_changes_model(self):
        payment = urllib.error.HTTPError("https://router.huggingface.co", 402, "quota", None, None)
        with (
            patch.dict(os.environ, ENV, clear=True),
            patch.object(router, "discover_hf_models", return_value=LIVE),
            patch.object(router.urllib.request, "urlopen", side_effect=payment) as hit,
        ):
            response = self.call()
        self.assertFalse(response["ok"])
        self.assertEqual(response["failures"][0]["status"], 402)
        self.assertEqual(hit.call_count, 1)

    def test_timeout_has_only_two_tries(self):
        with (
            patch.dict(os.environ, ENV, clear=True),
            patch.object(router, "discover_hf_models", return_value=LIVE),
            patch.object(router.urllib.request, "urlopen", side_effect=TimeoutError("slow")) as hit,
            patch.object(router.time, "sleep"),
        ):
            response = self.call()
        self.assertFalse(response["ok"])
        self.assertEqual(response["failures"][0]["attempts"], 2)
        self.assertEqual(hit.call_count, 2)


if __name__ == "__main__":
    unittest.main()
