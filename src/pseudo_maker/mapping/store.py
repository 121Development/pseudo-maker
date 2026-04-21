"""mapping.json schema and serialization."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ..substitute.mapper import MappingEntry

SCHEMA_VERSION = 1


def write_mapping(
    path: Path,
    entries: Iterable[MappingEntry],
    *,
    source_file: str | None = None,
) -> None:
    payload = {
        "version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_file": source_file,
        "entries": [
            {
                "id": e.id,
                "type": e.type,
                "original": e.original,
                "fake": e.fake,
                "aliases": sorted(e.aliases),
                "fake_aliases": dict(e.fake_aliases),
                "occurrences": e.occurrences,
            }
            for e in entries
        ],
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_mapping(path: Path) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("version") != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported mapping version: {payload.get('version')} (expected {SCHEMA_VERSION})"
        )
    return payload["entries"]
