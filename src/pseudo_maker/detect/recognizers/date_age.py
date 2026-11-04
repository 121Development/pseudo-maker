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
# "15 januari 2025", "1:a mars", "3 feb. 2024", "15:e jan"
_LONG = re.compile(
    rf"\b(3[01]|[12]\d|0?[1-9])(?::[ae])?\s+({_SV_MONTHS})\b\.?(?:\s+(19|20)\d{{2}}\b)?",
    re.IGNORECASE,
)

# Age — only with an explicit age cue. A bare "3 år" is usually a duration
# ("har arbetat 3 år"), so it is NOT matched.
#   "45 år gammal", "45 år ung", "45-årig", "45-åriga", "45-åring", "45 års ålder",
#   "ålder: 45", "ålder 45 år", "(45 år)"
_AGE = re.compile(
    r"\b(\d{1,3})\s*(?:år\s+(?:gammal|gamla|gammalt|ung)|-?årig[at]?|-?åring(?:en)?|års\s+ålder)\b"
    r"|\bålder(?:n)?\s*:?\s*(\d{1,3})(?:\s*år)?\b"
    r"|\((\d{1,3})\s*år\)",
    re.IGNORECASE,
)


class DateRecognizer:
    name = "DATE"

    def find(self, text: str) -> Iterable[Span]:
        for pat in (_ISO, _DMY, _LONG):
            for m in pat.finditer(text):
                value = m.group(0)
                yield Span(m.start(), m.start() + len(value), self.name, value, 0.7, "regex")


class AgeRecognizer:
    name = "AGE"

    def find(self, text: str) -> Iterable[Span]:
        for m in _AGE.finditer(text):
            n = int(next(g for g in m.groups() if g is not None))
            if 0 <= n <= 120:
                yield Span(m.start(), m.end(), self.name, m.group(0), 0.7, "regex")
