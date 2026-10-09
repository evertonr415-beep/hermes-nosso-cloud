"""Offline privacy and regression checks for opt-in memory chat."""
import ast
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WEB = (ROOT / "hermes-render-light-web.py").read_text()
SIMPLE = (ROOT / "hermes-simple.py").read_text()
DOCKER = (ROOT / "Dockerfile").read_text()

class MemoryErrorFake(Exception):
    pass

class FakeMemory:
    MemoryAccessError = MemoryErrorFake
    def __init__(self):
        self.calls = []
    def recover_record(self, key):
        self.calls.append(key)
        return "Lembrete sobre Arapongas"

class MemoryChatTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(WEB)
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "opt_in_memory_context")
        self.memory = FakeMemory()
        spec = importlib.util.spec_from_file_location("memory_router_test", ROOT / "hermes-global-model-router.py")
        router = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(router)
        scope = {"os": os, "memory": self.memory, "router": router}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "<memory_gate>", "exec"), scope)
        self.gate = scope["opt_in_memory_context"]

    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.gate("olá", {"use_memory": True}, "groq"), "olá")
            self.assertEqual(self.memory.calls, [])

    def test_explicit_consent_required(self):
        with patch.dict(os.environ, {"HERMES_MEMORY_CHAT_ENABLED": "1"}):
            self.assertEqual(self.gate("olá", {}, "groq"), "olá")
            self.assertEqual(self.gate("olá", {"use_memory": "true"}, "groq"), "olá")
            self.assertEqual(self.memory.calls, [])

    def test_anonymous_never_receives_memory(self):
        with patch.dict(os.environ, {"HERMES_MEMORY_CHAT_ENABLED": "1"}):
            self.assertEqual(self.gate("olá", {"use_memory": True}, "anonymous"), "olá")
            self.assertEqual(self.memory.calls, [])

    def test_authorized_request_uses_bounded_context(self):
        with patch.dict(os.environ, {"HERMES_MEMORY_CHAT_ENABLED": "1"}):
            result = self.gate("Arapongas", {"use_memory": True}, "groq")
        self.assertIn("Lembrete sobre Arapongas", result)
        self.assertTrue(result.endswith("Arapongas"))
        self.assertEqual(self.memory.calls, ["MEMORY.md", "USER.md"])

    def test_deployment_wires_real_module(self):
        self.assertIn("COPY hermes-memory-recovery.py /usr/local/bin/hermes-memory-recovery", DOCKER)
        self.assertIn('use_memory = msg.get("use_memory") is True', SIMPLE)
        self.assertIn("use-memory", WEB)
        self.assertIn("result = agent.answer(effective_prompt)", WEB)

if __name__ == "__main__":
    unittest.main()
