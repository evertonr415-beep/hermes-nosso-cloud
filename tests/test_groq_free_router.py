"""Offline regression tests for official Groq Free inference (no real API calls)."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
import urllib.error
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "hermes-global-model-router.py"
spec = importlib.util.spec_from_file_location("hermes_groq_test", path)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)

ENV = {
    "GROQ_API_KEY": "gsk_" + "x" * 36,
    "HF_TOKEN": "hf_" + "x" * 30,
    "HERMES_GLOBAL_ROUTER_ENABLED": "1",
    "HERMES_INFERENCE_MODE": "groq",
    "HERMES_GLOBAL_PROVIDERS_JSON": "[]",
    "HERMES_GLOBAL_KEYLESS_ALLOW": "0",
    "HERMES_PUBLIC_ANONYMOUS_ENABLED": "0",
}

class Response:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, *args):
        return json.dumps({"choices":[{"message":{"content":"OK"}}]}).encode()

class GroqFreeTests(unittest.TestCase):
    def query(self):
        return router.run({"prompt":"Responda OK.", "sensitivity":"normal",
                           "provider_id":"groq-free", "max_tokens":12})

    def test_only_groq_configured_on_free_mode(self):
        with patch.dict(os.environ, ENV, clear=True):
            cfg = router.configured()
        self.assertEqual([c["id"] for c in cfg], ["groq-free"])
        self.assertEqual(cfg[0]["model"], "qwen/qwen3.8-27b")

    def test_official_url_and_token_isolation(self):
        with (patch.dict(os.environ, ENV, clear=True),
              patch.object(router.urllib.request, "urlopen", return_value=Response()) as send):
            result = self.query()
        self.assertTrue(result["ok"])
        request = send.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(request.headers["Authorization"], "Bearer " + ENV["GROQ_API_KEY"])
        self.assertNotIn(ENV["HF_TOKEN"], request.data.decode())
        self.assertNotIn("MEMORY.md", request.data.decode())

    def test_missing_groq_key_makes_no_network_request(self):
        env = {k:v for k,v in ENV.items() if k != "GROQ_API_KEY"}
        with (patch.dict(os.environ, env, clear=True),
              patch.object(router.urllib.request, "urlopen") as send):
            result = self.query()
        self.assertFalse(result["ok"])
        send.assert_not_called()

    def test_429_does_not_retry(self):
        error = urllib.error.HTTPError("https://api.groq.com", 429, "limit", None, None)
        with (patch.dict(os.environ, ENV, clear=True),
              patch.object(router.urllib.request, "urlopen", side_effect=error) as send):
            result = self.query()
        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"][0]["status"], 429)
        self.assertEqual(send.call_count, 1)

    def test_403_org_model_permission_code_is_safely_classified(self):
        from io import BytesIO
        error = urllib.error.HTTPError(
            "https://api.groq.com", 403, "Forbidden", None,
            BytesIO(json.dumps({"error": {
                "code": "model_permission_blocked_org",
                "message": "Never echo this remote message or any secret",
            }}).encode()),
        )
        with (patch.dict(os.environ, ENV, clear=True),
              patch.object(router.urllib.request, "urlopen", side_effect=error) as send):
            result = self.query()
        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"][0]["status"], 403)
        self.assertEqual(result["failures"][0]["code"], "model_permission_blocked_org")
        self.assertNotIn("message", result["failures"][0])
        self.assertEqual(send.call_count, 1)

    def test_401_invalid_key_not_retried(self):
        error = urllib.error.HTTPError("https://api.groq.com", 401, "invalid", None, None)
        with (patch.dict(os.environ, ENV, clear=True),
              patch.object(router.urllib.request, "urlopen", side_effect=error) as send):
            result = self.query()
        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"][0]["status"], 401)
        self.assertEqual(send.call_count, 1)

    def test_another_documented_free_model_is_allowed(self):
        with patch.dict(os.environ, {**ENV, "HERMES_GROQ_MODEL": "openai/gpt-oss-20b"}, clear=True):
            self.assertEqual(router.configured()[0]["model"], "openai/gpt-oss-20b")

if __name__ == "__main__":
    unittest.main()
