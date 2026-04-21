from __future__ import annotations

import re
from typing import Iterable

from .base import Span

_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")


class EmailRecognizer:
    name = "EMAIL"

    def find(self, text: str) -> Iterable[Span]:
        for m in _PATTERN.finditer(text):
            yield Span(m.start(), m.end(), self.name, m.group(0), 1.0, "regex")
