from __future__ import annotations

import re
from typing import Iterable

from .base import Span

# Swedish license plate: 3 letters + 3 digits, OR 3 letters + 2 digits + 1 letter (since 2019).
# Excluded characters: I, Q, V (to avoid confusion).
_LETTERS = "ABCDEFGHJKLMNOPRSTUWXYZ"
_PATTERN = re.compile(
    rf"(?<![A-Z\d])([{_LETTERS}]{{3}})\s?(\d{{3}}|\d{{2}}[{_LETTERS}])(?![A-Z\d])"
)


class LicensePlateSeRecognizer:
    name = "LICENSE_PLATE"

    def find(self, text: str) -> Iterable[Span]:
        for m in _PATTERN.finditer(text):
            yield Span(m.start(), m.end(), self.name, m.group(0), 0.7, "regex")
