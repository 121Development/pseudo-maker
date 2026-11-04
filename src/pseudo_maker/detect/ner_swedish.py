"""Swedish NER via spaCy sv_core_news_lg.

Maps spaCy entity labels to pseudo-maker types, and applies a post-filter
that drops obvious false positives:

  - Single-token lowercase PERSON matches are almost always wrong (spaCy
    confuses common English nouns with Swedish given names).
  - Anything in the PERSON blocklist (e.g. "site", "turnover", "owner").
  - Spans containing "/" or matching a role word ("OWNER/FOUNDER").
  - LOC spans matching a country/continent name are passed through unchanged
    (not anonymized) — they're rarely identifying on their own.
  - LOC spans are split into CITY (single capitalized token, no digits/comma)
    vs STREET (anything else), so the substitution layer can pick the right
    fake generator.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable

from .blocklist import (
    is_blocklisted_company,
    is_blocklisted_person,
    is_country_or_continent,
)
from .recognizers.base import Span

_LABEL_MAP = {
    "PRS": "PERSON",
    "PER": "PERSON",
    "ORG": "COMPANY",
    "LOC": "LOCATION",
    "GPE": "LOCATION",
}


@lru_cache(maxsize=1)
def _load_model(model_name: str = "sv_core_news_lg"):
    import spacy
    return spacy.load(model_name)


_CITY_SHAPE = re.compile(r"^[A-ZÅÄÖ][a-zåäöéüè]+$")
_STREET_SUFFIXES = (
    "gatan", "vägen", "stigen", "torget", "gränd", "gränden", "allén",
    "esplanaden", "leden", "platsen", "plan", "kajen", "backen",
    "parken", "kullen", "åsen", "gången", "rondellen",
)


def _is_street_token(t: str) -> bool:
    lower = t.lower()
    return any(lower.endswith(suffix) for suffix in _STREET_SUFFIXES)


def _classify_location(text: str) -> str:
    """Return 'CITY' for a single city-like token, 'STREET' otherwise."""
    t = text.strip()
    # Street name ending (Slåttervallsgatan, Storgatan, Kungsvägen, …) wins
    # over single-token-city detection.
    if _is_street_token(t):
        return "STREET"
    if " " not in t and "," not in t and not any(c.isdigit() for c in t):
        if _CITY_SHAPE.match(t):
            return "CITY"
    return "STREET"


_LEADING_NOISE = re.compile(
    r"^(?:mainly|primarily|mostly|främst|huvudsakligen|ofta|endast|bara)\s+",
    re.IGNORECASE,
)


def _strip_leading_noise(text: str) -> tuple[str, int]:
    """Strip a leading adverb like 'mainly ' / 'huvudsakligen '.

    Returns (new_text, offset_adjustment) so callers can adjust the span start.
    """
    m = _LEADING_NOISE.match(text)
    if m:
        return text[m.end():], m.end()
    return text, 0


def _should_reject_person(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    if is_blocklisted_person(t):
        return True
    # Slash inside a name almost always means a role fragment was captured
    # ("OWNER/FOUNDER"). Safer to drop than try to salvage.
    if "/" in t:
        return True
    # Single lowercase token → probably a common noun mis-tagged.
    if " " not in t and t == t.lower():
        return True
    # Single all-uppercase token of role-word-like length → often a title fragment.
    if " " not in t and t.isupper() and len(t) <= 10:
        return True
    return False


def _should_reject_company(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    if "/" in t:
        return True
    # Tech products / jargon ("Teams", "Excel", "Slack") are tagged ORG a lot.
    if is_blocklisted_person(t) or is_blocklisted_company(t):
        return True
    return False


_CAPS_WORD = re.compile(r"\b[A-ZÅÄÖÉÜ]{3,}(?:-[A-ZÅÄÖÉÜ]{2,})*\b")


def _titlecase_caps(text: str) -> str:
    def fix(m: re.Match) -> str:
        w = m.group(0)
        return "-".join(p[0] + p[1:].lower() for p in w.split("-"))
    out = _CAPS_WORD.sub(fix, text)
    assert len(out) == len(text)
    return out


class SwedishNerRecognizer:
    name = "NER"

    def __init__(self, model_name: str = "sv_core_news_lg"):
        self._model_name = model_name
        self._nlp = None

    def _ensure(self):
        if self._nlp is None:
            self._nlp = _load_model(self._model_name)
        return self._nlp

    def find(self, text: str) -> Iterable[Span]:
        nlp = self._ensure()
        # spaCy misses names written in capitals ("MOHAMMED AL-HASSAN"), common
        # in Swedish headings and forms. Title-case all-caps words before NER;
        # same length, so offsets map straight back to the original text.
        doc = nlp(_titlecase_caps(text))
        for ent in doc.ents:
            mapped = _LABEL_MAP.get(ent.label_)
            if not mapped:
                continue

            span_text = text[ent.start_char:ent.end_char]
            start_char = ent.start_char
            end_char = ent.end_char

            # Strip a leading adverb like "mainly " that NER sometimes glues in.
            stripped, offset = _strip_leading_noise(span_text)
            if offset:
                span_text = stripped
                start_char += offset

            if mapped == "PERSON":
                if _should_reject_person(span_text):
                    continue
            elif mapped == "COMPANY":
                if _should_reject_company(span_text):
                    continue
            elif mapped == "LOCATION":
                if is_country_or_continent(span_text):
                    continue
                mapped = _classify_location(span_text)  # CITY or STREET

            yield Span(
                start=start_char,
                end=end_char,
                type=mapped,
                value=span_text,
                confidence=0.85,
                source="ner",
            )
