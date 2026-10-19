"""Offline regression tests for the opt-in local Ollama provider."""
import json
import os
import urllib.error
import importlib.util
from pathlib import Path
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "hermes_ollama_router_test", ROOT / "hermes-global-model-router.py"
)
router = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(router)

KEY = "local-bridge-test-key-" + "x" * 32
PROVIDER = {
    "id": "ollama-local",
    "url": "https://llama.sistemavotoforte.com.br/v1/chat/completions",
    "model": "llama3.2:3b",
    "api_key_env": "HERMES_LLAMA_BRIDGE_KEY",
    "priority": -30,
    "max_tokens": 512,
    "timeout": 20,
}
ENV = {
    "HERMES_GLOBAL_ROUTER_ENABLED": "1",
    "HERMES_INFERENCE_MODE": "groq",
    "HERMES_GLOBAL_PROVIDERS_JSON": json.dumps([PROVIDER]),
    "HERMES_GLOBAL_ALLOWED_PROVIDERS": "ollama-local",
    "HERMES_LLAMA_BRIDGE_KEY": KEY,
    "HERMES_GLOBAL_KEYLESS_ALLOW": "0",
    "HERMES_PUBLIC_ANONYMOUS_ENABLED": "0",
}


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, *args):
        return json.dumps({
            "choices": [{"message": {"content": "Llama bridge OK"}}]
        }).encode()


class OllamaProviderRouterTests(unittest.TestCase):
    def request(self):
        return {
            "prompt": "Responda OK.",
            "sensitivity": "normal",
            "provider_id": "ollama-local",
            "max_tokens": 64,
        }

    def test_provider_requires_allowlist_and_key(self):
        with patch.dict(os.environ, ENV, clear=True):
            self.assertEqual(
                [p["id"] for p in router.configured()], ["ollama-local"]
            )

        env = dict(ENV)
        env["HERMES_GLOBAL_ALLOWED_PROVIDERS"] = ""
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(router.configured(), [])

        env = dict(ENV)
        env.pop("HERMES_LLAMA_BRIDGE_KEY")
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(router.configured(), [])

    def test_routes_to_https_bridge_with_bearer_auth(self):
        with (
            patch.dict(os.environ, ENV, clear=True),
            patch.object(
                router.urllib.request, "urlopen", return_value=FakeResponse()
            ) as send,
        ):
            result = router.run(self.request())

        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "ollama-local")
        self.assertEqual(result["model"], "llama3.2:3b")
        self.assertEqual(result["response"], "Llama bridge OK")
        request = send.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://llama.sistemavotoforte.com.br/v1/chat/completions",
        )
        self.assertEqual(
            request.headers["Authorization"], "Bearer " + KEY
        )
        payload = json.loads(request.data.decode())
        self.assertEqual(payload["model"], "llama3.2:3b")
        self.assertFalse(payload["stream"])

    def test_explicit_local_route_does_not_silently_fallback(self):
        failure = urllib.error.URLError("private diagnostic must not escape")
        with (
            patch.dict(os.environ, ENV, clear=True),
            patch.object(
                router.urllib.request, "urlopen", side_effect=failure
            ) as send,
        ):
            result = router.run(self.request())

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["failures"][0]["provider"], "ollama-local"
        )
        self.assertNotIn("private diagnostic", str(result))
        self.assertEqual(send.call_count, 1)


if __name__ == "__main__":
    unittest.main()
