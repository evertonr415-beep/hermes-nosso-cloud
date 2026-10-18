import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "hermes_ollama_openai_bridge",
    ROOT / "hermes-ollama-openai-bridge.py",
)
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


class OllamaBridgePayloadTests(unittest.TestCase):
    def test_openai_chat_payload_converts_to_ollama_shape(self):
        payload = {
            "model": "llama3.2:3b",
            "messages": [
                {"role": "system", "content": "You are Hermes."},
                {"role": "user", "content": "Responda sim."},
            ],
            "max_tokens": 40,
            "temperature": 0.2,
            "stream": False,
        }
        converted = bridge.validate_payload(payload)
        self.assertEqual(converted["model"], "llama3.2:3b")
        self.assertEqual(converted["messages"], payload["messages"])
        self.assertEqual(converted["options"]["num_predict"], 40)
        self.assertFalse(converted["stream"])

    def test_rejects_other_models(self):
        with self.assertRaisesRegex(ValueError, "model_not_allowed"):
            bridge.validate_payload({
                "model": "another-model",
                "messages": [{"role": "user", "content": "hi"}],
            })

    def test_rejects_streaming(self):
        with self.assertRaisesRegex(ValueError, "streaming_not_supported"):
            bridge.validate_payload({
                "model": "llama3.2:3b",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            })

    def test_rejects_invalid_roles_and_large_prompts(self):
        with self.assertRaisesRegex(ValueError, "invalid_message"):
            bridge.validate_payload({
                "messages": [{"role": "tool", "content": "hi"}],
            })
        with self.assertRaisesRegex(ValueError, "prompt_too_large"):
            bridge.validate_payload({
                "messages": [{"role": "user", "content": "x" * 32001}],
            })

    def test_converts_ollama_text_to_openai_response(self):
        result = bridge.make_openai_response("llama3.2:3b", "Olá")
        self.assertEqual(result["object"], "chat.completion")
        self.assertEqual(
            result["choices"][0]["message"],
            {"role": "assistant", "content": "Olá"},
        )
        self.assertEqual(result["choices"][0]["finish_reason"], "stop")


if __name__ == "__main__":
    unittest.main()
