"""Offline tests for anonymous-only Hermes chat routing."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
import urllib.error
from unittest.mock import patch

mod_path = Path(__file__).resolve().parents[1] / "hermes-global-model-router.py"
spec = importlib.util.spec_from_file_location("anon_router", mod_path)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)
ENV = {
    "HF_TOKEN": "hf_" + "x" * 28,
    "HERMES_GLOBAL_ROUTER_ENABLED": "1",
    "HERMES_INFERENCE_MODE": "anonymous",
    "HERMES_PUBLIC_ANONYMOUS_ENABLED": "1",
    "HERMES_GLOBAL_KEYLESS_ALLOW": "0",
    "HERMES_GLOBAL_PROVIDERS_JSON": "[]",
}

class FakeResponse:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, *args):
        return json.dumps({"choices": [{"message": {"content": "OK"}}]}).encode()

class AnonymousRouterTests(unittest.TestCase):
    def call(self, sensitivity="public"):
        return router.run({"prompt": "Say OK", "sensitivity": sensitivity,
                           "provider_id": "anonymous-public", "max_tokens": 20})

    def test_with_hf_token_uses_only_public_provider(self):
        with patch.dict(os.environ, ENV, clear=True):
            providers = router.configured()
        self.assertEqual([p["id"] for p in providers], ["anonymous-public"])
        self.assertEqual(providers[0]["model"], "auto")

    def test_call_never_sends_hf_token(self):
        with patch.dict(os.environ, ENV, clear=True), \
             patch.object(router.urllib.request, "urlopen", return_value=FakeResponse()) as send:
            result = self.call()
        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "anonymous-public")
        request = send.call_args.args[0]
        self.assertEqual(request.full_url, "https://vireonix.ai/v1/chat/completions")
        self.assertFalse(any(k.lower() == "authorization" for k in request.headers))
        self.assertNotIn(ENV["HF_TOKEN"], request.data.decode("utf-8"))

    def test_normal_and_restricted_do_not_go_to_public(self):
        with patch.dict(os.environ, ENV, clear=True), \
             patch.object(router.urllib.request, "urlopen") as send:
            self.assertFalse(self.call("normal")["ok"])
            self.assertFalse(self.call("restricted")["ok"])
            send.assert_not_called()

    def test_anonymous_429_retries_only_once_and_not_to_hf(self):
        denied = urllib.error.HTTPError("https://vireonix.ai", 429, "rate", None, None)
        with patch.dict(os.environ, ENV, clear=True), \
             patch.object(router.urllib.request, "urlopen", side_effect=denied) as send, \
             patch.object(router.time, "sleep"):
            result = self.call()
        self.assertFalse(result["ok"])
        self.assertEqual(send.call_count, 2)

if __name__ == "__main__":
    unittest.main()
