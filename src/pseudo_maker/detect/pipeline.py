"""Detection pipeline: combine regex recognizers + Swedish NER, resolve overlaps."""
from __future__ import annotations

from typing import Iterable, Sequence

from .ner_swedish import SwedishNerRecognizer
from .recognizers.bankgiro_plusgiro import BankgiroRecognizer, PlusgiroRecognizer
from .recognizers.base import Span
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
        return _resolve_overlaps(spans)


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
