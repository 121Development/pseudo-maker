from __future__ import annotations

import re
from typing import Iterable

from .base import Span, luhn_check

# Swedish organisationsnummer: NNNNNN-NNNN (10 digits, optional dash, sometimes prefixed with country/16).
# The third digit must be >= 2 to distinguish from personnummer.
_PATTERN = re.compile(r"(?<!\d)(?:16)?(\d{6})[-]?(\d{4})(?!\d)")


def is_valid_orgnr(value: str) -> bool:
    digits = re.sub(r"[^\d]", "", value)
    if len(digits) == 12 and digits.startswith("16"):
        digits = digits[2:]
    if len(digits) != 10:
        return False
    # Third digit (index 2) must be >= 2 — that's how Skatteverket distinguishes orgnr from pnr.
    if int(digits[2]) < 2:
        return False
    return luhn_check(digits)


class OrgnrRecognizer:
    name = "ORGNR"

    def find(self, text: str) -> Iterable[Span]:
        for m in _PATTERN.finditer(text):
            value = m.group(0)
            if is_valid_orgnr(value):
                yield Span(m.start(), m.end(), self.name, value, 1.0, "regex")
