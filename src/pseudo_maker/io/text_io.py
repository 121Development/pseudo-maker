"""Plain text and Markdown I/O — full text in/out, no structure to preserve."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence


def read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def apply_replacements(text: str, replacements: Sequence[tuple[int, int, str]]) -> str:
    """Apply (start, end, replacement) tuples right-to-left to avoid index drift."""
    pieces: list[str] = []
    out = text
    for start, end, repl in sorted(replacements, key=lambda r: r[0], reverse=True):
        out = out[:start] + repl + out[end:]
    return out
