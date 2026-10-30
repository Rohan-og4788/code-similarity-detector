"""Validation helpers for untrusted uploaded files.

Uploaded files are only ever *read as text*. They are never imported,
executed, compiled to bytecode for execution, or written to disk.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

MIN_FILES = 2
DEFAULT_MAX_FILES = 20
HARD_MAX_FILES = 50
DEFAULT_MAX_FILE_BYTES = 1 * 1024 * 1024      # 1 MB per file (default)
HARD_MAX_FILE_BYTES = 2 * 1024 * 1024         # upper bound for the setting
MAX_TOTAL_BYTES = 10 * 1024 * 1024            # 10 MB per analysis
MAX_FILENAME_LENGTH = 100

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


@dataclass(frozen=True)
class UploadLimits:
    """Limits applied while validating a batch of uploads."""

    max_files: int = DEFAULT_MAX_FILES
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_total_bytes: int = MAX_TOTAL_BYTES

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not MIN_FILES <= self.max_files <= HARD_MAX_FILES:
            errors.append(f"Maximum file count must be between {MIN_FILES} and {HARD_MAX_FILES}.")
        if not 1024 <= self.max_file_bytes <= HARD_MAX_FILE_BYTES:
            errors.append("Maximum file size must be between 1 KB and 2 MB.")
        return errors


def sanitize_filename(raw: str) -> str:
    """Return a safe display name: no directories, no control characters."""
    name = raw.replace("\\", "/").split("/")[-1]
    name = _CONTROL_CHARS.sub("", name).strip()
    if len(name) > MAX_FILENAME_LENGTH:
        stem, ext = os.path.splitext(name)
        name = stem[: MAX_FILENAME_LENGTH - len(ext)] + ext
    return name


def has_py_extension(name: str) -> bool:
    """True if the name ends in .py and has a non-empty stem."""
    return name.lower().endswith(".py") and len(name) > 3


def decode_source(data: bytes) -> str:
    """Decode bytes to text (UTF-8, then Windows-1252) and normalize newlines.

    Raises ValueError with a user-friendly message when decoding is impossible.
    """
    if b"\x00" in data:
        raise ValueError("File looks binary (it contains NUL bytes), not Python text.")
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("File could not be decoded as UTF-8 or Windows-1252 text.")
    return text.replace("\r\n", "\n").replace("\r", "\n")
