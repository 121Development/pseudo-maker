from __future__ import annotations

import re
from typing import Iterable

from stdnum.eu import vat

from .base import Span

# EU VAT: country code (2 letters) + numeric/alphanumeric body
_PATTERN = re.compile(r"\b([A-Z]{2}\s?[A-Z0-9]{2,12})\b")


class VatRecognizer:
    name = "VAT"

    def find(self, text: str) -> Iterable[Span]:
        for m in _PATTERN.finditer(text):
            value = m.group(0)
            try:
                if vat.is_valid(value):
                    yield Span(m.start(), m.end(), self.name, value, 1.0, "regex")
            except Exception:
                continue
