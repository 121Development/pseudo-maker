from __future__ import annotations

import re
from typing import Iterable

from stdnum import luhn

from .base import Span

_PATTERN = re.compile(r"(?<!\d)(?:\d[\s\-]?){12,18}\d(?!\d)")


class CreditCardRecognizer:
    name = "CREDIT_CARD"

    def find(self, text: str) -> Iterable[Span]:
        for m in _PATTERN.finditer(text):
            value = m.group(0)
            digits = re.sub(r"[\s\-]", "", value)
            if 13 <= len(digits) <= 19 and luhn.is_valid(digits):
                yield Span(m.start(), m.end(), self.name, value, 0.95, "regex")
