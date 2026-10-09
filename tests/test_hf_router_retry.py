"""Offline regression tests for the official Hugging Face Hermes router."""
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
    "HERMES_HF_MODEL": "Qwen/Qwen2.5-7B-Instruct",
    "HERMES_GLOBAL_PROVIDERS_JSON": "[]",
    "HERMES_GLOBAL_KEYLESS_ALLOW": "0",
}


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, *args):
        return json.dumps({"choices": [{"message": {"content": "OK"}}]}).encode()


class HuggingFaceRouterTests(unittest.TestCase):
    def call(self):
        return router.run({
            "prompt": "Olá", "provider_id": "huggingface-official",
            "sensitivity": "normal", "max_tokens": 16,
        })

    def test_default_model_is_qwen_not_llama(self):
        with patch.dict(os.environ, ENV, clear=True):
            self.assertEqual(router.configured()[0]["model"], "Qwen/Qwen2.5-7B-Instruct")

    def test_transient_503_retries_once_then_succeeds(self):
        unavailable = urllib.error.HTTPError("https://router.huggingface.co", 503, "unavailable", None, None)
        with patch.dict(os.environ, ENV, clear=True), \
             patch.object(router.urllib.request, "urlopen", side_effect=[unavailable, FakeResponse()]) as get, \
             patch.object(router.time, "sleep"):
            result = self.call()
        self.assertTrue(result["ok"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(get.call_count, 2)

    def test_payment_required_not_retried(self):
        payment = urllib.error.HTTPError("https://router.huggingface.co", 402, "payment", None, None)
        with patch.dict(os.environ, ENV, clear=True), \
             patch.object(router.urllib.request, "urlopen", side_effect=payment) as get:
            result = self.call()
        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"][0]["status"], 402)
        self.assertEqual(result["failures"][0]["attempts"], 1)
        self.assertEqual(get.call_count, 1)

    def test_timeout_retries_at_most_twice(self):
        with patch.dict(os.environ, ENV, clear=True), \
             patch.object(router.urllib.request, "urlopen", side_effect=TimeoutError("timed out")) as get, \
             patch.object(router.time, "sleep"):
            result = self.call()
        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"][0]["attempts"], 2)
        self.assertEqual(get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
