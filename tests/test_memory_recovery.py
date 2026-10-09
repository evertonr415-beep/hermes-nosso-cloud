"""Tests for encrypted memory recovery without remote requests."""
import importlib.util
import json
import base64
import hashlib
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

spec = importlib.util.spec_from_file_location("memrec", Path(__file__).resolve().parents[1] / "hermes-memory-recovery.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class FakeResponse:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, n):
        return self.data[:n]

class MemoryRecoveryTests(unittest.TestCase):
    def test_round_trip(self):
        key = "ab" * 32
        plaintext = "Hermes memória".encode()
        nonce = bytes(range(12))
        encrypted = AESGCM(bytes.fromhex(key)).encrypt(nonce, plaintext, None)
        record = dict(iv=base64.b64encode(nonce).decode(),
                      ciphertext=base64.b64encode(encrypted).decode(),
                      content_sha256=hashlib.sha256(plaintext).hexdigest())
        def opener(req, timeout):
            self.assertEqual(json.loads(req.data)["action"], "get")
            self.assertEqual(timeout, 8)
            return FakeResponse(json.dumps(dict(ok=True, record=record)).encode())
        params = dict(endpoint=mod.EXPECTED_URL, token="cd"*32, aes_key=key, opener=opener)
        self.assertEqual(mod.recover_record("MEMORY.md", **params), plaintext.decode())
        with self.assertRaises(mod.MemoryAccessError):
            mod.recover_record("MEMORY.md", **dict(params, aes_key="ef"*32))
        record["content_sha256"] = "00"*32
        with self.assertRaises(mod.MemoryAccessError):
            mod.recover_record("MEMORY.md", **params)

    def test_invalid_authorization(self):
        def opener(*args, **kwargs):
            self.fail("network should not be used")
        params = dict(endpoint=mod.EXPECTED_URL, token="", aes_key="ab"*32, opener=opener)
        with self.assertRaises(mod.MemoryAccessError):
            mod.recover_record("MEMORY.md", **params)
        params["token"] = "cd"*32
        with self.assertRaises(mod.MemoryAccessError):
            mod.recover_record("../MEMORY.md", **params)

if __name__ == "__main__":
    unittest.main()
