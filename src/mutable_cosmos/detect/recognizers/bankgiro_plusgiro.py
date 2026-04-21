from __future__ import annotations

import re
from typing import Iterable

from .base import Span, luhn_check

# Bankgiro: 7 or 8 digits, formatted XXX-XXXX or XXXX-XXXX
# Plusgiro: 2-8 digits + check digit, formatted with dash before last digit, e.g. 12 34 56-7
_BG_PATTERN = re.compile(r"(?<!\d)(\d{3,4})-(\d{4})(?!\d)")
_PG_PATTERN = re.compile(r"(?<!\d)((?:\d[\s]?){1,8}\d)-(\d)(?!\d)")


class BankgiroRecognizer:
    name = "BANKGIRO"

    def find(self, text: str) -> Iterable[Span]:
        for m in _BG_PATTERN.finditer(text):
            digits = m.group(1) + m.group(2)
            if 7 <= len(digits) <= 8 and luhn_check(digits):
                yield Span(m.start(), m.end(), self.name, m.group(0), 1.0, "regex")


class PlusgiroRecognizer:
    name = "PLUSGIRO"

    def find(self, text: str) -> Iterable[Span]:
        for m in _PG_PATTERN.finditer(text):
            digits = re.sub(r"[\s-]", "", m.group(0))
            if 3 <= len(digits) <= 9 and luhn_check(digits):
                yield Span(m.start(), m.end(), self.name, m.group(0), 0.85, "regex")
