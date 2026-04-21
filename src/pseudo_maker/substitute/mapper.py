"""Stable input→fake mapping with alias coalescing."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .fakes import generate_fake


def _normalize(value: str) -> str:
    return " ".join(value.split()).lower()


@dataclass
class MappingEntry:
    id: str
    type: str
    original: str
    fake: str
    aliases: set[str] = field(default_factory=set)
    # Map original-side alias → fake-side rendering used in the cleaned doc.
    # Lets restore know "Karin" alone in the LLM output should become "Anna".
    fake_aliases: dict[str, str] = field(default_factory=dict)
    occurrences: int = 0


class Mapper:
    """Owns the (type, normalized_original) → MappingEntry table for one document."""

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self._by_key: dict[tuple[str, str], MappingEntry] = {}
        self._used_fakes: set[str] = set()
        self._next_id = 1

    def _new_id(self) -> str:
        eid = f"ent_{self._next_id:04d}"
        self._next_id += 1
        return eid

    def _unique_fake(self, entity_type: str, original: str) -> str:
        for _ in range(50):
            candidate = generate_fake(entity_type, original, self.rng)
            if candidate not in self._used_fakes and candidate != original:
                self._used_fakes.add(candidate)
                return candidate
        # Last-resort suffix to guarantee uniqueness
        candidate = f"{candidate}_{self.rng.randint(1000, 9999)}"
        self._used_fakes.add(candidate)
        return candidate

    def map(self, entity_type: str, original: str) -> MappingEntry:
        """Return the entry for this (type, original). Creates one if first seen.

        Alias rule: if the entity is a PERSON or COMPANY and `original` is a token
        subset of an existing entry's original (e.g. "Anna" inside "Anna Andersson"),
        and that existing entry is unique on the alias, reuse it as an alias.
        """
        key = (entity_type, _normalize(original))
        if key in self._by_key:
            entry = self._by_key[key]
            entry.occurrences += 1
            return entry

        if entity_type in ("PERSON", "COMPANY"):
            tokens = original.split()
            if len(tokens) == 1:
                candidates = [
                    e for (t, _), e in self._by_key.items()
                    if t == entity_type and tokens[0].lower() in _normalize(e.original).split()
                ]
                if len(candidates) == 1:
                    entry = candidates[0]
                    entry.aliases.add(original)
                    entry.fake_aliases[original] = self.fake_for_alias(entry, original)
                    entry.occurrences += 1
                    self._by_key[key] = entry
                    return entry

        entry = MappingEntry(
            id=self._new_id(),
            type=entity_type,
            original=original,
            fake=self._unique_fake(entity_type, original),
            occurrences=1,
        )
        self._by_key[key] = entry
        return entry

    def fake_for_alias(self, entry: MappingEntry, alias_text: str) -> str:
        """When an alias (e.g. just first name) is encountered, derive a matching shorter fake."""
        if alias_text == entry.original:
            return entry.fake
        if entry.type == "PERSON":
            # Use first token of fake to match a single-token alias
            tokens = entry.fake.split()
            if len(alias_text.split()) == 1 and tokens:
                return tokens[0]
        return entry.fake

    def get_entry(self, entity_id: str) -> MappingEntry:
        for entry in self._by_key.values():
            if entry.id == entity_id:
                return entry
        raise KeyError(f"unknown entity_id: {entity_id}")

    def override_fake(self, entity_id: str, new_fake: str) -> None:
        """Replace an entry's fake with a user-supplied value.

        Drops the old fake from ``_used_fakes``, records the new one, and for
        PERSON entries re-derives ``fake_aliases`` so single-name aliases in
        the cleaned doc still round-trip via the refreshed first-name slice.
        Raises ``KeyError`` if no entry with the given id is tracked.
        """
        new_fake = (new_fake or "").strip()
        if not new_fake:
            raise ValueError("new_fake must be a non-empty string")

        for entry in self._by_key.values():
            if entry.id == entity_id:
                self._used_fakes.discard(entry.fake)
                entry.fake = new_fake
                self._used_fakes.add(new_fake)
                if entry.type == "PERSON":
                    entry.fake_aliases = {
                        alias: self.fake_for_alias(entry, alias)
                        for alias in entry.aliases
                    }
                return
        raise KeyError(f"unknown entity_id: {entity_id}")

    def all_entries(self) -> list[MappingEntry]:
        seen_ids: set[str] = set()
        out: list[MappingEntry] = []
        for entry in self._by_key.values():
            if entry.id in seen_ids:
                continue
            seen_ids.add(entry.id)
            out.append(entry)
        return out
