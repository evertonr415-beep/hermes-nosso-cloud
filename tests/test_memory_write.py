"""Offline tests for explicit, privacy-preserving memory writes."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("hermes_memory_write", ROOT / "hermes-memory-write.py")
writer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(writer)


class MemoryWriteTests(unittest.TestCase):
    def test_appends_entry_to_persistent_memory_location(self):
        with TemporaryDirectory() as tmp:
            saved = writer.save_memory_entry("Minha palavra de teste é JATOBÁ-731", root=tmp)
            path = Path(tmp) / "memories" / "MEMORY.md"
            self.assertEqual(saved, "Minha palavra de teste é JATOBÁ-731")
            self.assertIn(saved, path.read_text(encoding="utf-8"))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_rejects_empty_or_oversized_entries(self):
        with TemporaryDirectory() as tmp:
            for value in ("   ", "x" * 1001):
                with self.subTest(value_length=len(value)):
                    with self.assertRaises(writer.MemoryWriteError):
                        writer.save_memory_entry(value, root=tmp)

    def test_rejects_credential_like_content(self):
        with TemporaryDirectory() as tmp:
            for value in ("password=supersecret", "api_key: example", "Bearer abcdefghijklmnop"):
                with self.subTest(value=value):
                    with self.assertRaises(writer.MemoryWriteError):
                        writer.save_memory_entry(value, root=tmp)
            path = Path(tmp) / "memories" / "MEMORY.md"
            self.assertFalse(path.exists())

    def test_caps_file_size(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp) / "memories"
            directory.mkdir()
            (directory / "MEMORY.md").write_text("x" * writer.MAX_FILE_BYTES, encoding="utf-8")
            with self.assertRaises(writer.MemoryWriteError):
                writer.save_memory_entry("não cabe", root=tmp)


if __name__ == "__main__":
    unittest.main()
