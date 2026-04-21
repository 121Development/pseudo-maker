"""Shared pytest fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest
from docx import Document


@pytest.fixture
def fixture_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def sample_docx(tmp_path: Path) -> Path:
    """A small .docx with mixed PII, formatted runs, a table, and a header."""
    doc = Document()
    doc.add_heading("Klientärende", level=1)

    p = doc.add_paragraph()
    p.add_run("Klienten ").bold = False
    p.add_run("Anna Andersson").bold = True
    p.add_run(" har personnummer 850612-1238 och bor på Storgatan 5, 411 23 Göteborg. ")
    p.add_run("Anna").bold = True
    p.add_run(" arbetar hos Volvo AB (organisationsnummer 556036-0793).")

    doc.add_paragraph("Telefon: 070-123 45 67")
    doc.add_paragraph("E-post: anna.andersson@example.se")
    doc.add_paragraph("Plusgiro: 12 34 56-7   Bankgiro: 5402-9706")

    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Mottagare"
    table.cell(0, 1).text = "Belopp"
    table.cell(1, 0).text = "Erik Svensson"
    table.cell(1, 1).text = "5 000 kr"

    section = doc.sections[0]
    section.header.paragraphs[0].text = "Konfidentiellt - Anna Andersson"

    out = tmp_path / "sample.docx"
    doc.save(str(out))
    return out
