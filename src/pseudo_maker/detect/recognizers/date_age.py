from __future__ import annotations

import re
from typing import Iterable

from .base import Span

# Common date formats:
#   2024-01-15, 2024/01/15, 15/01/2024, 15 januari 2024, 15 jan 2024
_ISO = re.compile(r"\b(19|20)\d{2}[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b")
_DMY = re.compile(r"\b(0[1-9]|[12]\d|3[01])[/.](0[1-9]|1[0-2])[/.](19|20)\d{2}\b")

_SV_MONTHS = (
    "januari|februari|mars|april|maj|juni|juli|augusti|"
    "september|oktober|november|december|jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec"
)
_LONG = re.compile(rf"\b([12]?\d|3[01])\s+({_SV_MONTHS})(?:\s+(19|20)\d{{2}})?\b", re.IGNORECASE)

# Age — only with a cue word, otherwise far too many false positives.
_AGE = re.compile(r"\b(\d{1,3})\s*(?:år\s+gammal|års?(?:\s+ålder)?)\b", re.IGNORECASE)


class DateRecognizer:
    name = "DATE"

    def find(self, text: str) -> Iterable[Span]:
        for pat in (_ISO, _DMY, _LONG):
            for m in pat.finditer(text):
                yield Span(m.start(), m.end(), self.name, m.group(0), 0.7, "regex")


class AgeRecognizer:
    name = "AGE"

    def find(self, text: str) -> Iterable[Span]:
        for m in _AGE.finditer(text):
            try:
                n = int(m.group(1))
            except ValueError:
                continue
            if 0 <= n <= 120:
                yield Span(m.start(), m.end(), self.name, m.group(0), 0.7, "regex")
