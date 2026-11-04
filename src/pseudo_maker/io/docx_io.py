"""Read/write .docx with run-level formatting preservation.

The model: a document is a list of `paragraphs` from the body, all table cells
(recursively), all headers and footers. Each paragraph holds an ordered list of
runs (`<w:r>`), where each run carries formatting (bold, italic, font, ...).

To replace text spanning runs while keeping formatting, we:
  1. Build the paragraph's full text and a list of run-boundary offsets.
  2. Detection produces (start, end, replacement) on the full text.
  3. We apply replacements right-to-left, rewriting only the affected runs.
     If a replacement is fully inside one run, we splice in place — all
     formatting is preserved exactly.
     If a replacement spans multiple runs, we put the replacement in the first
     affected run (inheriting its formatting), keep the suffix after the
     entity in the last affected run's tail, and blank intermediate runs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

from docx import Document
from docx.document import Document as DocumentT
from docx.table import _Cell


@dataclass
class ParagraphHandle:
    """A single paragraph plus everything we need to rewrite its text."""
    paragraph: object  # docx.text.paragraph.Paragraph
    full_text: str
    run_offsets: list[int]  # start offset of each run within full_text


def _iter_paragraphs(doc: DocumentT) -> Iterator[object]:
    """Walk every paragraph in body, tables (recursively), headers, footers."""
    yield from doc.paragraphs
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from _iter_cell(cell)
    for section in doc.sections:
        # Always-present header/footer:
        for hf in (section.header, section.footer):
            yield from _iter_header_footer(hf)
        # Optional first-page / even-page header/footers: accessing these on
        # python-docx lazily instantiates missing parts from its template
        # directory, which may not be present (e.g. PyInstaller). Only iterate
        # them when the section actually opts in.
        if getattr(section, "different_first_page_header_footer", False):
            for hf in (section.first_page_header, section.first_page_footer):
                yield from _iter_header_footer(hf)
        try:
            even = section.part.package.settings.element.find(
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}evenAndOddHeaders"
            )
        except Exception:
            even = None
        if even is not None:
            for hf in (section.even_page_header, section.even_page_footer):
                yield from _iter_header_footer(hf)


def _iter_header_footer(hf) -> Iterator[object]:
    if hf is None:
        return
    try:
        paragraphs = hf.paragraphs
    except FileNotFoundError:
        return
    yield from paragraphs
    for table in hf.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from _iter_cell(cell)


def _iter_cell(cell: _Cell) -> Iterator[object]:
    yield from cell.paragraphs
    for table in cell.tables:
        for row in table.rows:
            for inner in row.cells:
                yield from _iter_cell(inner)


def _build_handle(paragraph) -> ParagraphHandle:
    offsets: list[int] = []
    cursor = 0
    parts: list[str] = []
    for run in paragraph.runs:
        offsets.append(cursor)
        parts.append(run.text or "")
        cursor += len(run.text or "")
    return ParagraphHandle(paragraph=paragraph, full_text="".join(parts), run_offsets=offsets)


def load(path: Path) -> tuple[DocumentT, list[ParagraphHandle]]:
    doc = Document(str(path))
    handles = [_build_handle(p) for p in _iter_paragraphs(doc)]
    return doc, handles


def save(doc: DocumentT, path: Path) -> None:
    doc.save(str(path))


def apply_paragraph_replacements(
    handle: ParagraphHandle,
    replacements: Sequence[tuple[int, int, str]],
) -> None:
    """Apply (start, end, replacement) substitutions to a paragraph's runs."""
    if not replacements:
        return
    runs = list(handle.paragraph.runs)
    if not runs:
        return

    sorted_repls = sorted(replacements, key=lambda r: r[0], reverse=True)
    for start, end, repl in sorted_repls:
        offsets = [0]
        for r in runs:
            offsets.append(offsets[-1] + len(r.text or ""))
        # offsets[i] = start of run i; offsets[-1] = total length

        # Find first run whose end > start
        first_idx = None
        for i in range(len(runs)):
            if offsets[i + 1] > start:
                first_idx = i
                break
        if first_idx is None:
            if start == offsets[-1]:
                # Insertion at the very end of the paragraph: append to last run.
                runs[-1].text = (runs[-1].text or "") + repl
            continue
        # Find last run whose start < end
        last_idx = first_idx
        for i in range(first_idx, len(runs)):
            if offsets[i] < end:
                last_idx = i
            else:
                break

        offset_in_first = start - offsets[first_idx]
        offset_in_last = end - offsets[last_idx]

        first_text = runs[first_idx].text or ""
        last_text = runs[last_idx].text or ""

        if first_idx == last_idx:
            new_text = first_text[:offset_in_first] + repl + first_text[offset_in_last:]
            runs[first_idx].text = new_text
        else:
            runs[first_idx].text = first_text[:offset_in_first] + repl + last_text[offset_in_last:]
            for i in range(first_idx + 1, last_idx + 1):
                runs[i].text = ""

    handle.full_text = "".join((r.text or "") for r in runs)
    handle.run_offsets = []
    cursor = 0
    for r in runs:
        handle.run_offsets.append(cursor)
        cursor += len(r.text or "")
