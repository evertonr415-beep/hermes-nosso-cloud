"""Offline tests for the opt-in owner-hosted OpenAI-compatible provider.

These tests make no network calls and do not require credentials or a running
local model. The endpoint must be HTTPS and expose /chat/completions.
"""
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "hermes-global-model-router.py"
spec = importlib.util.spec_from_file_location("hermes_local_provider_test", path)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)

PROVIDER = {
    "id": "llama-local",
    "url": "https://llama.example.invalid/v1/chat/completions",
    "model": "llama3.2:3b",
    "api_key_env": "HERMES_LLAMA_BRIDGE_KEY",
    "priority": 0,
    "max_tokens": 256,
    "timeout": 8,
}

BASE_ENV = {
    "HERMES_GLOBAL_ROUTER_ENABLED": "1",
    "HERMES_INFERENCE_MODE": "groq",
    "HERMES_GLOBAL_ALLOWED_PROVIDERS": "llama-local",
    "HERMES_GLOBAL_PROVIDERS_JSON": json.dumps([PROVIDER]),
    "HERMES_LLAMA_BRIDGE_KEY": "test-only-token-not-a-real-secret",
    "GROQ_API_KEY": "",
    "HF_TOKEN": "",
    "HERMES_GLOBAL_KEYLESS_ALLOW": "0",
    "HERMES_PUBLIC_ANONYMOUS_ENABLED": "0",
}


class MockResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, *args):
        return json.dumps({
            "choices": [{"message": {"content": "LLAMA_TEST_OK"}}]
        }).encode("utf-8")


class OwnerHostedProviderTests(unittest.TestCase):
    def test_owner_provider_is_opt_in_and_uses_allowlist(self):
        with patch.dict(os.environ, BASE_ENV, clear=True):
            providers = router.configured()
        self.assertEqual([p["id"] for p in providers], ["llama-local"])
        self.assertEqual(providers[0]["url"], PROVIDER["url"])

    def test_provider_rejected_when_not_allowlisted(self):
        env = {**BASE_ENV, "HERMES_GLOBAL_ALLOWED_PROVIDERS": ""}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(router.configured(), [])

    def test_provider_rejected_without_secret(self):
        env = {k: v for k, v in BASE_ENV.items()
               if k != "HERMES_LLAMA_BRIDGE_KEY"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(router.configured(), [])

    def test_provider_rejected_for_plain_http(self):
        invalid = {**PROVIDER, "url": "http://llama.example.invalid/v1/chat/completions"}
        env = {**BASE_ENV, "HERMES_GLOBAL_PROVIDERS_JSON": json.dumps([invalid])}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(router.configured(), [])

    def test_request_uses_bearer_auth_and_openai_compatible_shape(self):
        with (patch.dict(os.environ, BASE_ENV, clear=True),
              patch.object(router.urllib.request, "urlopen",
                           return_value=MockResponse()) as send):
            result = router.run({
                "prompt": "Responda apenas LLAMA_TEST_OK.",
                "sensitivity": "normal",
                "provider_id": "llama-local",
                "max_tokens": 32,
            })
        self.assertTrue(result["ok"])
        self.assertEqual(result["response"], "LLAMA_TEST_OK")
        request = send.call_args.args[0]
        self.assertEqual(request.full_url, PROVIDER["url"])
        self.assertEqual(
            request.headers["Authorization"],
            "Bearer " + BASE_ENV["HERMES_LLAMA_BRIDGE_KEY"],
        )
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "llama3.2:3b")
        self.assertEqual(body["messages"][-1]["content"], "Responda apenas LLAMA_TEST_OK.")
        self.assertNotIn(BASE_ENV["HERMES_LLAMA_BRIDGE_KEY"], request.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
