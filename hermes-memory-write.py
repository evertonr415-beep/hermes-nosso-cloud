#!/usr/bin/env python3
"""Safe local append helper for explicitly requested Hermes memory entries."""
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

_LOCK = threading.Lock()
MAX_ENTRY_CHARS = 1000
MAX_FILE_BYTES = 128000
SENSITIVE_LINE = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|secret[_-]?key|private[_-]?key|"
    r"password|passwd|authorization|senha|token)\s*[:=]"
)
SENSITIVE_VALUE = re.compile(
    r"(?i)(?:sk-(?:proj-)?|ghp_|gho_|github_pat_|Bearer\s+)[A-Za-z0-9_-]{10,}"
)


class MemoryWriteError(ValueError):
    """Safe, user-displayable memory write failure."""


def save_memory_entry(text, root="/opt/data"):
    """Append one explicit, bounded, non-secret entry without following symlinks."""
    if not isinstance(text, str):
        raise MemoryWriteError("invalid_entry")
    entry = " ".join(text.split()).strip()
    if not entry or len(entry) > MAX_ENTRY_CHARS:
        raise MemoryWriteError("invalid_entry")
    if SENSITIVE_LINE.search(entry) or SENSITIVE_VALUE.search(entry):
        raise MemoryWriteError("sensitive_entry")
    root_path = Path(root).resolve()
    directory = root_path / "memories"
    target = directory / "MEMORY.md"
    with _LOCK:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink() or not directory.resolve().is_relative_to(root_path):
            raise MemoryWriteError("invalid_memory_path")
        if target.is_symlink():
            raise MemoryWriteError("invalid_memory_path")
        try:
            size = target.stat().st_size if target.exists() else 0
        except OSError:
            raise MemoryWriteError("memory_unavailable") from None
        line = "- " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + ": " + entry + "\n"
        encoded = line.encode("utf-8")
        if size + len(encoded) > MAX_FILE_BYTES:
            raise MemoryWriteError("memory_full")
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(target, flags, 0o600)
            try:
                os.fchmod(fd, 0o600)
                os.write(fd, encoded)
            finally:
                os.close(fd)
        except OSError:
            raise MemoryWriteError("memory_unavailable") from None
    return entry
