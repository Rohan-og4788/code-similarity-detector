"""Turn raw uploads into validated, in-memory SourceFile objects."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Sequence

from utils.helpers import format_size
from utils.validators import (
    UploadLimits,
    decode_source,
    has_py_extension,
    sanitize_filename,
)


@dataclass(frozen=True)
class SourceFile:
    """A validated Python source file held only in memory."""

    index: int            # position in the original upload list
    name: str             # safe, unique display name
    size: int             # size in bytes
    text: str             # decoded source (newlines normalized)
    line_count: int
    renamed_from: str | None = None

    @classmethod
    def from_text(cls, name: str, text: str, index: int = 0) -> "SourceFile":
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return cls(index, name, len(text.encode("utf-8")), text, len(text.splitlines()))


@dataclass(frozen=True)
class RejectedFile:
    index: int
    name: str
    reason: str


@dataclass
class ProcessedUploads:
    accepted: list[SourceFile] = field(default_factory=list)
    rejected: list[RejectedFile] = field(default_factory=list)


def _unique_name(name: str, used: set[str]) -> str:
    if name.lower() not in used:
        return name
    stem, ext = os.path.splitext(name)
    counter = 2
    while f"{stem} ({counter}){ext}".lower() in used:
        counter += 1
    return f"{stem} ({counter}){ext}"


def process_uploads(items: Sequence[tuple[str, bytes]], limits: UploadLimits) -> ProcessedUploads:
    """Validate uploads. Never executes or stores the content.

    ``items`` is a list of ``(filename, raw_bytes)``. Files that fail a check
    are returned in ``rejected`` with a plain-language reason; duplicate
    filenames are kept but renamed ("a.py" -> "a (2).py").
    """
    result = ProcessedUploads()
    used: set[str] = set()
    total = 0
    for index, (raw_name, data) in enumerate(items):
        name = sanitize_filename(raw_name)
        shown = name or "(unnamed)"

        def reject(reason: str, _shown: str = shown, _index: int = index) -> None:
            result.rejected.append(RejectedFile(_index, _shown, reason))

        if not has_py_extension(name):
            reject("Only .py files are supported.")
            continue
        if len(data) == 0:
            reject("File is empty.")
            continue
        if len(data) > limits.max_file_bytes:
            reject(f"File is {format_size(len(data))}; the per-file limit is {format_size(limits.max_file_bytes)}.")
            continue
        try:
            text = decode_source(data)
        except ValueError as exc:
            reject(str(exc))
            continue
        if not text.strip():
            reject("File contains only whitespace.")
            continue
        if len(result.accepted) >= limits.max_files:
            reject(f"Too many files; the limit is {limits.max_files}.")
            continue
        if total + len(data) > limits.max_total_bytes:
            reject(f"Adding this file would exceed the total upload limit of {format_size(limits.max_total_bytes)}.")
            continue

        unique = _unique_name(name, used)
        used.add(unique.lower())
        total += len(data)
        result.accepted.append(
            SourceFile(
                index=index,
                name=unique,
                size=len(data),
                text=text,
                line_count=len(text.splitlines()),
                renamed_from=name if unique != name else None,
            )
        )
    return result
