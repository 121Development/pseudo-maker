"""Swedish case / diary numbers used by myndigheter, kommuner and courts.

  Dnr KS 2024/123 · Diarienummer: 3.1.2-4567/2023 · Ärende 2025/1187
  Mål nr T 1234-23 · Målnummer B 567-24 · Ref.nr 2024-0815
Requires a cue word; the number on its own is too ambiguous.
"""
from __future__ import annotations

import re
from typing import Iterable

from .base import Span

_PATTERN = re.compile(
    r"\b(?:dnr|d\.nr|diarie(?:nummer|nr)|ärende(?:nummer|nr)?|mål(?:nummer|[ \t]+nr)|"
    r"ref(?:erens)?(?:nummer|\.?[ \t]?nr)|beslut(?:snummer|[ \t]+nr)|akt(?:nummer|[ \t]+nr))"
    r"\.?[ \t]*:?[ \t]*"
    r"((?:[A-ZÅÄÖ]{1,4}[ \t]?)?\d{1,6}(?:[./:\-]\d{1,6}){1,4})",
    re.IGNORECASE,
)


class CaseNumberSeRecognizer:
    name = "CASE_NUMBER"

    def find(self, text: str) -> Iterable[Span]:
        for m in _PATTERN.finditer(text):
            yield Span(m.start(1), m.end(1), self.name, m.group(1), 0.9, "regex")
