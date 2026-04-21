from __future__ import annotations

import re
from typing import Iterable

from .base import Span, luhn_check

# Accepts YYMMDD[-+]XXXX, YYMMDDXXXX, YYYYMMDD[-]XXXX, YYYYMMDDXXXX
# Bounded by non-digit / start-end so we don't grab parts of longer numbers.
_PATTERNS = [
    re.compile(r"(?<!\d)(\d{8})[-]?(\d{4})(?!\d)"),       # 12-digit form
    re.compile(r"(?<!\d)(\d{6})([-+]?)(\d{4})(?!\d)"),    # 10-digit form
]


def _normalize_to_10(value: str) -> str | None:
    """Strip separators, return YYMMDDXXXX (10 digits) or None if shape wrong."""
    digits = re.sub(r"[-+]", "", value)
    if len(digits) == 12:
        digits = digits[2:]
    if len(digits) != 10:
        return None
    return digits


def is_valid_personnummer(value: str) -> bool:
    d = _normalize_to_10(value)
    if not d:
        return False
    yy, mm, dd = int(d[:2]), int(d[2:4]), int(d[4:6])
    # Samordningsnummer: day is real_day + 60
    if dd > 60:
        dd -= 60
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return False
    # The 9-digit body for Luhn is YYMMDD + 3-digit serial
    body9 = d[:9]
    return luhn_check(body9 + d[9])


class PersonnummerRecognizer:
    name = "PERSONNUMMER"

    def find(self, text: str) -> Iterable[Span]:
        seen: set[tuple[int, int]] = set()
        for pat in _PATTERNS:
            for m in pat.finditer(text):
                start, end = m.start(), m.end()
                if (start, end) in seen:
                    continue
                value = m.group(0)
                if is_valid_personnummer(value):
                    seen.add((start, end))
                    yield Span(start, end, self.name, value, 1.0, "regex")
