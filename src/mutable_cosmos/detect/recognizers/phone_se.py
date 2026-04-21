from __future__ import annotations

import re
from typing import Iterable

from .base import Span

# Swedish mobile/landline:
#   +46 70 123 45 67  /  +46(0)70-1234567  /  070-123 45 67  /  08-123 456
# Tolerate spaces, dashes, parens. Require leading + or 0 to avoid grabbing arbitrary digit groups.
_PATTERN = re.compile(
    r"(?<![\w/])(?:\+46[\s\-]?(?:\(0\)[\s\-]?)?|0)(?:\d[\s\-]?){6,11}\d(?![\d/])"
)


class PhoneSeRecognizer:
    name = "PHONE"

    def find(self, text: str) -> Iterable[Span]:
        for m in _PATTERN.finditer(text):
            value = m.group(0).strip()
            digits_only = re.sub(r"[^\d+]", "", value)
            # Require 7-13 digits total (Sweden: 8-10 significant digits)
            digit_count = sum(c.isdigit() for c in digits_only)
            if 7 <= digit_count <= 13:
                yield Span(m.start(), m.end(), self.name, value, 0.9, "regex")
