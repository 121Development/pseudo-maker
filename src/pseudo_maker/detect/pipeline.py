"""Detection pipeline: combine regex recognizers + Swedish NER, resolve overlaps."""
from __future__ import annotations

import re
from typing import Sequence

from .ner_swedish import SwedishNerRecognizer
from .recognizers.bankgiro_plusgiro import BankgiroRecognizer, PlusgiroRecognizer
from .recognizers.base import Span
from .recognizers.company_street_se import (
    CompanySeRecognizer,
    KnownCompanySeRecognizer,
    StreetSeRecognizer,
)
from .recognizers.case_number_se import CaseNumberSeRecognizer
from .recognizers.credit_card import CreditCardRecognizer
from .recognizers.date_age import AgeRecognizer, DateRecognizer
from .recognizers.email import EmailRecognizer
from .recognizers.iban import IbanRecognizer
from .recognizers.ip_url import IpRecognizer, UrlRecognizer
from .recognizers.license_plate_se import LicensePlateSeRecognizer
from .recognizers.orgnr import OrgnrRecognizer
from .recognizers.passport import PassportRecognizer
from .recognizers.personnummer import PersonnummerRecognizer
from .recognizers.phone_se import PhoneSeRecognizer
from .recognizers.postal_code_se import PostalCodeSeRecognizer
from .recognizers.vat import VatRecognizer


def _default_regex_recognizers():
    return [
        # Order matters slightly: high-precision first so overlaps prefer them.
        PersonnummerRecognizer(),
        OrgnrRecognizer(),
        CaseNumberSeRecognizer(),
        IbanRecognizer(),
        CreditCardRecognizer(),
        VatRecognizer(),
        BankgiroRecognizer(),
        PlusgiroRecognizer(),
        EmailRecognizer(),
        UrlRecognizer(),
        IpRecognizer(),
        PhoneSeRecognizer(),
        LicensePlateSeRecognizer(),
        PassportRecognizer(),
        PostalCodeSeRecognizer(),
        DateRecognizer(),
        AgeRecognizer(),
        StreetSeRecognizer(),
        CompanySeRecognizer(),
        KnownCompanySeRecognizer(),
    ]


class DetectionPipeline:
    def __init__(self, *, use_ner: bool = True, ner_model: str = "sv_core_news_lg"):
        self.regex_recognizers = _default_regex_recognizers()
        self.ner = SwedishNerRecognizer(ner_model) if use_ner else None

    def detect(self, text: str) -> list[Span]:
        spans: list[Span] = []
        for r in self.regex_recognizers:
            spans.extend(r.find(text))
        if self.ner is not None:
            spans.extend(self.ner.find(text))
        spans = [_extend_street_number(text, s) for s in spans]
        return _resolve_overlaps(spans)


_HOUSE_NUMBER = re.compile(r"[ \t]+\d{1,4}(?:[A-Za-z]|[ \t][A-Z])?(?![\wåäö])")


def propagate_person_names(texts: Sequence[str], spans_per_text: list[list[Span]]) -> list[list[Span]]:
    """Find further mentions of names that NER caught somewhere in the document.

    spaCy is inconsistent: it may tag "Johanna Ek" but miss "Ek noterade ..."
    two sentences later, or tag "MOHAMMED AL-HASSAN" but miss "Fatima
    Al-Hassan". Every name part of a detected PERSON is searched for across
    the whole document (Title Case or ALL CAPS, optional genitive -s). A known
    first name directly before a found surname is included in the span.
    """
    from .. import swedish as sv
    from .blocklist import is_blocklisted_person

    parts: set[str] = set()
    for spans in spans_per_text:
        for s in spans:
            if s.type != "PERSON":
                continue
            for tok in s.value.split():
                if tok.lower() in sv.NAME_PARTICLES or len(tok) < 2 or is_blocklisted_person(tok):
                    continue
                if tok.isupper():
                    tok = "-".join(p[:1] + p[1:].lower() for p in tok.split("-"))
                parts.add(tok)
    if not parts:
        return spans_per_text

    alts = "|".join(re.escape(p) for p in sorted(parts, key=len, reverse=True))
    alts_upper = "|".join(re.escape(p.upper()) for p in sorted(parts, key=len, reverse=True))
    pat = re.compile(rf"(?<![\w\-])(?:{alts}|{alts_upper})(?:s|S)?(?![\w\-])")
    first_before = re.compile(r"([A-ZÅÄÖÉ][a-zåäöéü]+(?:-[A-ZÅÄÖÉ][a-zåäöéü]+)?)[ \t]+$")

    out: list[list[Span]] = []
    for text, spans in zip(texts, spans_per_text):
        new = list(spans)
        for m in pat.finditer(text):
            start, end = m.start(), m.end()
            if any(start < s.end and s.start < end for s in new):
                continue
            fm = first_before.search(text, 0, start)
            if fm and sv.is_known_first_name(fm.group(1)) and not any(
                fm.start(1) < s.end and s.start < start for s in new
            ):
                start = fm.start(1)
            new.append(Span(start, end, "PERSON", text[start:end], 0.75, "ner"))
        new.sort(key=lambda s: s.start)
        out.append(new)
    return out


def _extend_street_number(text: str, span: Span) -> Span:
    """NER often tags just 'Storgatan' in 'Storgatan 12B'; pull in the number."""
    if span.type != "STREET" or span.source != "ner" or any(c.isdigit() for c in span.value):
        return span
    m = _HOUSE_NUMBER.match(text, span.end)
    if not m:
        return span
    end = m.end()
    return Span(span.start, end, span.type, text[span.start:end], span.confidence, span.source)


def _resolve_overlaps(spans: Sequence[Span]) -> list[Span]:
    """When two spans overlap, keep the higher-priority one.

    Priority: regex > ner; longer > shorter; earlier > later (stable).
    """
    def priority(s: Span) -> tuple:
        return (
            0 if s.source == "regex" else 1,   # regex wins
            -(s.end - s.start),                # longer wins
            s.start,                           # earlier wins
        )
    sorted_spans = sorted(spans, key=priority)
    accepted: list[Span] = []
    for s in sorted_spans:
        if not any(_overlaps(s, a) for a in accepted):
            accepted.append(s)
    accepted.sort(key=lambda s: s.start)
    return accepted


def _overlaps(a: Span, b: Span) -> bool:
    return a.start < b.end and b.start < a.end
