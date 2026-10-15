"""Offline tests for the isolated agent-browser worker; never launch a browser."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch, MagicMock

source = Path(__file__).resolve().parents[1] / "agent-browser-worker" / "server.py"
spec = importlib.util.spec_from_file_location("agent_browser_worker", source)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class BrowserWorkerTests(unittest.TestCase):
    def test_exact_allowlist_and_https_only(self):
        hosts = ["docs.example.org"]
        self.assertEqual(
            worker.validate_target("https://docs.example.org/guide#section", hosts),
            "https://docs.example.org/guide",
        )
        for url in (
            "http://docs.example.org/",
            "https://evil.example/",
            "https://docs.example.org:8443/",
            "https://user:pass@docs.example.org/",
            "https://localhost/",
            "file:///etc/passwd",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                worker.validate_target(url, hosts)

    def test_allowlist_rejects_invalid_and_local_hosts(self):
        for value in ("localhost", "127.0.0.1", "example.local", "*.example.org", "bad host"):
            with self.subTest(value=value), patch.object(worker, "RAW_ALLOWED", value):
                with self.assertRaises(ValueError):
                    worker.allowed_hosts()

    def test_read_page_uses_fixed_commands_and_caps_output(self):
        opened = MagicMock(returncode=0, stdout="ok", stderr="")
        page = "x" * (worker.MAX_OUTPUT + 1)
        snapshot = MagicMock(returncode=0, stdout=page, stderr="")
        with patch.object(worker.subprocess, "run", side_effect=[opened, snapshot]) as run:
            result = worker.read_page("https://docs.example.org/", ["docs.example.org"])
        self.assertEqual(len(result["content"]), worker.MAX_OUTPUT)
        self.assertTrue(result["truncated"])
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0][:4],
                         ["agent-browser", "--allowed-domains", "docs.example.org", "open"])
        self.assertNotIn("shell", run.call_args_list[0].kwargs)
        self.assertEqual(run.call_args_list[1].args[0][-3:], ["-c", "-d", "5"])

    def test_browser_timeout_is_bounded(self):
        with patch.object(worker.subprocess, "run", side_effect=subprocess.TimeoutExpired("agent-browser", 18)):
            self.assertEqual(worker.read_page("https://docs.example.org/", ["docs.example.org"]),
                             {"error": "browser_timeout"})

    def test_browser_failure_does_not_return_stderr(self):
        failed = MagicMock(returncode=1, stdout="", stderr="private details")
        with patch.object(worker.subprocess, "run", return_value=failed):
            result = worker.read_page("https://docs.example.org/", ["docs.example.org"])
        self.assertEqual(result, {"error": "navigation_failed"})
        self.assertNotIn("private details", str(result))


if __name__ == "__main__":
    unittest.main()
