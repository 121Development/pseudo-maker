from __future__ import annotations

import re
from typing import Iterable

from stdnum import iban

from .base import Span

# IBAN: 2 letters + 2 digits + up to 30 alphanum, often grouped in 4s by spaces.
_PATTERN = re.compile(r"\b([A-Z]{2}\d{2}(?:[\s]?[A-Z0-9]{1,4}){1,7})\b")


class IbanRecognizer:
    name = "IBAN"

    def find(self, text: str) -> Iterable[Span]:
        for m in _PATTERN.finditer(text):
            value = m.group(0)
            try:
                if iban.is_valid(value):
                    yield Span(m.start(), m.end(), self.name, value, 1.0, "regex")
            except Exception:
                continue
