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


# Three-letter tokens that are followed by numbers in normal Swedish text and
# must not be taken for plates ("SEK 500", "ISO 900", "EUR 250", "SFS 199").
_NOT_PLATES = {
    "SEK", "EUR", "USD", "GBP", "NOK", "DKK", "CHF", "JPY", "ISO", "SFS", "SOU",
    "PRS", "AFS", "BFS", "KAP", "MOM", "TEL", "FAX", "NUM", "ART", "REF", "VER",
    "NRS", "LAS", "LOU", "PBL", "ABL", "AML", "FAR", "BFN", "RFR", "GDP", "BNP",
}


class LicensePlateSeRecognizer:
    name = "LICENSE_PLATE"

    def find(self, text: str) -> Iterable[Span]:
        for m in _PATTERN.finditer(text):
            if m.group(1) in _NOT_PLATES:
                continue
            yield Span(m.start(), m.end(), self.name, m.group(0), 0.7, "regex")
