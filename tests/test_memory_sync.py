"""Offline tests for Hermes encrypted sync; no production Supabase calls."""
import base64
import importlib.util
import json
import os
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MODULE_PATH = Path(__file__).resolve().parents[1] / "hermes-memory-sync.py"
spec = importlib.util.spec_from_file_location("hermes_memory_sync_under_test", MODULE_PATH)
memory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory)


class MemoryCryptoTests(TestCase):
    def test_encrypted_chunk_round_trip_and_random_nonce(self):
        key = bytes(range(32))
        original = "Memória de teste: acentuação e caracteres 🌎"
        with patch.object(memory, "HEXKEY", key.hex()):
            iv1, ciphertext1 = memory.encode_chunk(original)
            iv2, ciphertext2 = memory.encode_chunk(original)
        nonce1, nonce2 = base64.b64decode(iv1), base64.b64decode(iv2)
        self.assertEqual(len(nonce1), 12)
        self.assertNotEqual(nonce1, nonce2)
        self.assertNotEqual(ciphertext1, ciphertext2)
        self.assertEqual(AESGCM(key).decrypt(nonce1, base64.b64decode(ciphertext1), None).decode(), original)

    def test_wrong_key_cannot_decrypt(self):
        with patch.object(memory, "HEXKEY", "01" * 32):
            iv, encrypted = memory.encode_chunk("protegido")
        with self.assertRaises(Exception):
            AESGCM(bytes.fromhex("02" * 32)).decrypt(
                base64.b64decode(iv), base64.b64decode(encrypted), None
            )

    def test_strip_common_credentials(self):
        raw = "Informação útil\npassword: segredo\napi_key=exemplo\nÚltima linha"
        safe = memory.strip_secrets(raw)
        self.assertIn("Informação útil", safe)
        self.assertIn("Última linha", safe)
        self.assertNotIn("segredo", safe)
        self.assertNotIn("api_key=exemplo", safe)

    def test_config_fails_closed_without_secrets(self):
        with patch.object(memory, "TOKEN", ""), patch.object(memory, "HEXKEY", ""):
            self.assertFalse(memory.configuration_ok())

    def test_lexical_vector_is_bounded(self):
        vec = memory.lexical_embedding("Arapongas Arapongas")
        self.assertEqual(len(vec), 384)
        self.assertTrue(all(-1.0 <= x <= 1.0 for x in vec))


if __name__ == "__main__":
    main()
