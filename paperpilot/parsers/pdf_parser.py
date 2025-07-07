from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from paperpilot.parsers.sections import ParsedAsset, ParsedSection, extract_equation_blocks, extract_figure_captions, split_sections


def extract_pdf_layout_text(path: Path) -> str:
    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        columns = text.split("\n\n")
        if len(columns) > 1 and all(len(part) < len(text) * 0.7 for part in columns[:2]):
            chunks.append("\n".join(columns))
        else:
            chunks.append(text)
    return "\n\n".join(chunks).strip()


def parse_paper_text(text: str) -> tuple[list[ParsedSection], list[ParsedAsset]]:
    sections = split_sections(text)
    assets = extract_figure_captions(text) + extract_equation_blocks(text)
    return sections, assets


def parse_pdf_file(path: Path) -> tuple[list[ParsedSection], list[ParsedAsset], str]:
    text = extract_pdf_layout_text(path)
    sections, assets = parse_paper_text(text)
    return sections, assets, text
