#!/usr/bin/env python3
"""Mirrors owner-approved Hermes Markdown memory to authenticated Supabase memory.

Encrypts records before upload. Embeddings are deterministic 384-D lexical hashes,
not a claim of semantic embedding quality. No third-party model/API is contacted.
"""
import base64
import hashlib
import json
import math
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path("/opt/data")
STATE = ROOT / ".hermes-memory-sync-state.json"
FILES = ("MEMORY.md", "USER.md")
API = os.environ.get("HERMES_MEMORY_SYNC_URL", "").strip()
TOKEN = os.environ.get("HERMES_MEMORY_SYNC_TOKEN", "").strip()
HEXKEY = os.environ.get("HERMES_MEMORY_AES_KEY", "").strip()
CHUNK = 16000
MAX_FILE_BYTES = 256000
MAX_DEPTH = 6
IGNORED = {".git", "node_modules", ".cache", "cache", "backups", "backup", "plugins",
           "skills", "tmp", "temp", "venv", ".venv", "dist", "build", "trash"}
SENSITIVE_LINE = re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|secret[_-]?key|"
                             r"private[_-]?key|password|passwd|authorization)\s*[:=]")
SENSITIVE_VALUE = re.compile(r"(?i)(?:sk-(?:proj-)?|ghp_|gho_|github_pat_|Bearer\s+)[A-Za-z0-9_-]{10,}")

def configuration_ok():
    return (re.fullmatch(r"[0-9a-fA-F]{64}", TOKEN or "") is not None and
            re.fullmatch(r"[0-9a-fA-F]{64}", HEXKEY or "") is not None and
            API == "https://aufsewqtybpothlrsjij.supabase.co/functions/v1/hermes-global-memory")

def candidates():
    paths = []
    for base in (ROOT, ROOT / "home", ROOT / "home/.hermes",
                 ROOT / "profiles/default", ROOT / "workspace",
                 ROOT / "memories", ROOT / "memory"):
        for filename in FILES:
            path = base / filename
            if path.is_file() and not path.is_symlink():
                paths.append(path)
    seen = set(paths)
    examined = 0
    for folder, subdirs, filenames in os.walk(ROOT, followlinks=False):
        relative = Path(folder).relative_to(ROOT)
        if len(relative.parts) > MAX_DEPTH:
            subdirs[:] = []
            continue
        subdirs[:] = [d for d in subdirs if d not in IGNORED and
                      not (Path(folder) / d).is_symlink()]
        for name in filenames:
            examined += 1
            if examined > 6000:
                return paths
            if name in FILES:
                path = Path(folder) / name
                if path not in seen and not path.is_symlink():
                    seen.add(path)
                    paths.append(path)
    return paths

def find_memory_files():
    """Choose newest allowed real file of each requested name, no archives."""
    result = {}
    for file in candidates():
        try:
            stat = file.stat()
            if not file.resolve().is_relative_to(ROOT.resolve()):
                continue
            if stat.st_size < 1 or stat.st_size > MAX_FILE_BYTES:
                continue
            name = file.name
            if name not in result or stat.st_mtime > result[name].stat().st_mtime:
                result[name] = file
        except (OSError, ValueError):
            continue
    return result

def strip_secrets(text):
    lines = []
    for line in text.splitlines():
        if SENSITIVE_LINE.search(line) or SENSITIVE_VALUE.search(line):
            lines.append("[redacted sensitive configuration]")
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"

def lexical_embedding(text):
    # Feature hashing: searchable by lexical similarity, not semantic intent.
    vec = [0.0] * 384
    tokens = re.findall(r"[^\W_]{2,}", text.lower(), flags=re.UNICODE)
    for term in tokens[:10000]:
        digest = hashlib.sha256(term.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % 384
        sign = 1 if digest[4] & 1 else -1
        vec[index] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    if norm:
        vec = [round(v / norm, 7) for v in vec]
    return vec

def call(body):
    payload = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        API, data=payload, method="POST",
        headers={"Authorization": "Bearer " + TOKEN,
                 "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read(8192)
        result = json.loads(raw)
        if not isinstance(result, dict) or not result.get("ok"):
            raise ValueError("Memory server rejected operation")
        return result

def encode_chunk(chunk):
    iv = secrets.token_bytes(12)
    cipher = AESGCM(bytes.fromhex(HEXKEY)).encrypt(iv, chunk.encode("utf-8"), None)
    return base64.b64encode(iv).decode("ascii"), base64.b64encode(cipher).decode("ascii")

def state_load():
    try:
        data = json.loads(STATE.read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def state_save(data):
    STATE.parent.mkdir(exist_ok=True, parents=True)
    temp = STATE.with_name(".hermes-memory-state-" + secrets.token_hex(6))
    try:
        temp.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        temp.chmod(0o600)
        os.replace(temp, STATE)
    finally:
        temp.unlink(missing_ok=True)

def synchronize():
    if not configuration_ok():
        print("[hermes-memory] disabled: protected configuration incomplete", flush=True)
        return False
    paths = find_memory_files()
    state = state_load()
    if not paths:
        print("[hermes-memory] no MEMORY.md or USER.md in configured volume", flush=True)
        return False
    changed = 0
    for filename in FILES:
        file = paths.get(filename)
        if not file:
            continue
        try:
            raw = file.read_text(encoding="utf-8")
            safe = strip_secrets(raw)
            chunks = [safe[i:i + CHUNK] for i in range(0, len(safe), CHUNK)][:16]
            fingerprint = hashlib.sha256(safe.encode("utf-8")).hexdigest()
            prior = state.get(filename, {})
            if prior.get("sha") == fingerprint and prior.get("count") == len(chunks):
                continue
            for index, chunk in enumerate(chunks):
                name = filename if len(chunks) == 1 else f"{filename}:{index:04d}"
                iv, ciphertext = encode_chunk(chunk)
                call({"action":"put", "key":name, "iv":iv,
                      "ciphertext":ciphertext,
                      "content_sha256":hashlib.sha256(chunk.encode("utf-8")).hexdigest(),
                      "embedding":lexical_embedding(chunk)})
            old_count = int(prior.get("count", 0))
            if old_count > len(chunks):
                for index in range(len(chunks), min(old_count, 16)):
                    name = filename if old_count == 1 else f"{filename}:{index:04d}"
                    call({"action":"delete","key":name})
            state[filename] = {"sha":fingerprint,"count":len(chunks),
                               "updated_at":int(time.time())}
            state_save(state)
            changed += 1
            print(f"[hermes-memory] synchronized {filename} chunks={len(chunks)}",flush=True)
        except (OSError, UnicodeError, ValueError, urllib.error.URLError) as exc:
            print(f"[hermes-memory] failed {filename}: {type(exc).__name__}",flush=True)
    return changed > 0

if __name__ == "__main__":
    if "--check" in sys.argv:
        print(json.dumps({"configured":configuration_ok(),
                          "files":sorted(find_memory_files()),
                          "algorithm":"AES-256-GCM + lexical-384"},default=str))
        sys.exit(0)
    synchronize()
