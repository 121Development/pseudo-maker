from __future__ import annotations

import re
from typing import Iterable

from .base import Span

_IPV4 = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
_IPV6 = re.compile(r"\b(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}\b", re.IGNORECASE)
_URL = re.compile(r"\bhttps?://[^\s<>\"')]+", re.IGNORECASE)


class IpRecognizer:
    name = "IP"

    def find(self, text: str) -> Iterable[Span]:
        for pat in (_IPV4, _IPV6):
            for m in pat.finditer(text):
                yield Span(m.start(), m.end(), self.name, m.group(0), 1.0, "regex")


class UrlRecognizer:
    name = "URL"

    def find(self, text: str) -> Iterable[Span]:
        for m in _URL.finditer(text):
            yield Span(m.start(), m.end(), self.name, m.group(0), 1.0, "regex")
