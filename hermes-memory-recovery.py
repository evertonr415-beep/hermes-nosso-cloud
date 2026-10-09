#!/usr/bin/env python3
"""Read encrypted Hermes owner memory through the existing authenticated Edge Function.

Fail-closed library: no public HTTP routes, no plaintext CLI output, no writes to
disk, no automated injection into model prompts. The caller must separately
authorize any use of the returned plaintext.
"""
import base64
import binascii
import hashlib
import json
import os
import re
import urllib.error
import urllib.request

EXPECTED_URL = "https://aufsewqtybpothlrsjij.supabase.co/functions/v1/hermes-global-memory"
ALLOWED_KEY = re.compile(r"(?:MEMORY|USER)\.md(?::\d{4})?\Z")
TOKEN_RE = re.compile(r"[a-f0-9]{64}\Z")
MAX_RESPONSE_BYTES = 65536
MAX_PLAINTEXT_BYTES = 8192


class MemoryAccessError(Exception):
    """Generic non-secret memory access failure."""


def recover_record(name, *, endpoint=None, token=None, aes_key=None, opener=None):
    """Return verified UTF-8 plaintext for one explicitly named owner memory key.

    Enforces the exact owner-only Edge Function URL, configured bearer token,
    AES-256-GCM integrity and SHA-256 content hash. Never logs a secret.
    This is a server-side helper and must not be exposed directly to users.
    """
    if not isinstance(name, str) or ALLOWED_KEY.fullmatch(name) is None:
        raise MemoryAccessError("invalid_memory_key")
    endpoint = endpoint if endpoint is not None else os.getenv("HERMES_MEMORY_SYNC_URL", "")
    token = token if token is not None else os.getenv("HERMES_MEMORY_SYNC_TOKEN", "")
    aes_key = aes_key if aes_key is not None else os.getenv("HERMES_MEMORY_AES_KEY", "")
    if endpoint != EXPECTED_URL or not isinstance(token, str) or not TOKEN_RE.fullmatch(token):
        raise MemoryAccessError("memory_not_configured")
    if not isinstance(aes_key, str) or not TOKEN_RE.fullmatch(aes_key):
        raise MemoryAccessError("memory_not_configured")
    opener = opener or urllib.request.urlopen
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"action": "get", "key": name}).encode("utf-8"),
        method="POST",
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json",
                 "Accept": "application/json"},
    )
    try:
        with opener(request, timeout=8) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise MemoryAccessError("memory_response_too_large")
        body = json.loads(raw)
        if not isinstance(body, dict) or body.get("ok") is not True:
            raise MemoryAccessError("memory_read_denied")
        record = body.get("record")
        if not isinstance(record, dict):
            raise MemoryAccessError("memory_invalid_record")
        iv, cipher, digest = record.get("iv"), record.get("ciphertext"), record.get("content_sha256")
        if not all(isinstance(s, str) for s in (iv, cipher, digest)):
            raise MemoryAccessError("memory_invalid_record")
        if not TOKEN_RE.fullmatch(digest):
            raise MemoryAccessError("memory_invalid_record")
        try:
            nonce = base64.b64decode(iv, validate=True)
            encrypted = base64.b64decode(cipher, validate=True)
        except (ValueError, binascii.Error):
            raise MemoryAccessError("memory_invalid_record") from None
        if len(nonce) != 12 or not 17 <= len(encrypted) <= MAX_PLAINTEXT_BYTES + 16:
            raise MemoryAccessError("memory_invalid_record")
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        plain = AESGCM(bytes.fromhex(aes_key)).decrypt(nonce, encrypted, None)
        if len(plain) > MAX_PLAINTEXT_BYTES:
            raise MemoryAccessError("memory_invalid_record")
        if hashlib.sha256(plain).hexdigest() != digest:
            raise MemoryAccessError("memory_integrity_failed")
        return plain.decode("utf-8")
    except MemoryAccessError:
        raise
    except (urllib.error.URLError, OSError, ValueError, UnicodeError, KeyError, TypeError,
            json.JSONDecodeError, Exception) as error:
        # Do not leak network errors, backend payloads, ciphertext or keys.
        raise MemoryAccessError("memory_unavailable") from None
