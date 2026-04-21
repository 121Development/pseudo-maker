from __future__ import annotations

import re
from typing import Iterable

from .base import Span

# Swedish passport numbers are 8 digits. Many countries use 6-9 alphanumeric.
# We require a "pass"/"passport" cue word nearby to keep precision; otherwise too many false positives.
_PATTERN = re.compile(
    r"(?i)(?:pass(?:port)?(?:nummer|nr|no|number)?[:\s\-]+)([A-Z0-9]{6,9})"
)


class PassportRecognizer:
    name = "PASSPORT"

    def find(self, text: str) -> Iterable[Span]:
        for m in _PATTERN.finditer(text):
            yield Span(m.start(1), m.end(1), self.name, m.group(1), 0.85, "regex")
