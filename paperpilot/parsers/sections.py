from __future__ import annotations

import re
from dataclasses import dataclass

SECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("abstract", re.compile(r"^\s*abstract\s*$", re.IGNORECASE | re.MULTILINE)),
    ("introduction", re.compile(r"^\s*(?:\d+\.?\s*)?introduction\s*$", re.IGNORECASE | re.MULTILINE)),
    ("related_work", re.compile(r"^\s*(?:\d+\.?\s*)?related work\s*$", re.IGNORECASE | re.MULTILINE)),
    ("methodology", re.compile(r"^\s*(?:\d+\.?\s*)?(?:methodology|methods|approach)\s*$", re.IGNORECASE | re.MULTILINE)),
    ("experiments", re.compile(r"^\s*(?:\d+\.?\s*)?experiments?\s*$", re.IGNORECASE | re.MULTILINE)),
    ("results", re.compile(r"^\s*(?:\d+\.?\s*)?results?\s*$", re.IGNORECASE | re.MULTILINE)),
    ("conclusion", re.compile(r"^\s*(?:\d+\.?\s*)?conclusions?\s*$", re.IGNORECASE | re.MULTILINE)),
    ("references", re.compile(r"^\s*(?:\d+\.?\s*)?references?\s*$", re.IGNORECASE | re.MULTILINE)),
    ("appendix", re.compile(r"^\s*(?:\d+\.?\s*)?appendix\s*$", re.IGNORECASE | re.MULTILINE)),
]


@dataclass
class ParsedSection:
    section_key: str
    title: str
    content: str
    order_index: int


@dataclass
class ParsedAsset:
    asset_type: str
    label: str
    content: str


def normalize_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def split_sections(text: str) -> list[ParsedSection]:
    matches: list[tuple[int, str, str]] = []
    for key, pattern in SECTION_PATTERNS:
        for match in pattern.finditer(text):
            matches.append((match.start(), key, match.group(0).strip()))
    if not matches:
        return [ParsedSection("body", "Body", text.strip(), 0)]
    matches.sort(key=lambda item: item[0])
    sections: list[ParsedSection] = []
    for index, (start, key, title) in enumerate(matches):
        end = matches[index + 1][0] if index + 1 < len(matches) else len(text)
        chunk = text[start:end]
        header_end = chunk.find("\n")
        body = chunk[header_end + 1 :].strip() if header_end >= 0 else chunk.strip()
        sections.append(ParsedSection(key, title, normalize_whitespace(body), index))
    return sections


def extract_figure_captions(text: str) -> list[ParsedAsset]:
    assets: list[ParsedAsset] = []
    figure_pattern = re.compile(r"(Figure\s+\d+[:.]?\s*.+?)(?=Figure\s+\d+|Table\s+\d+|$)", re.IGNORECASE | re.DOTALL)
    table_pattern = re.compile(r"(Table\s+\d+[:.]?\s*.+?)(?=Figure\s+\d+|Table\s+\d+|$)", re.IGNORECASE | re.DOTALL)
    for match in figure_pattern.finditer(text):
        assets.append(ParsedAsset("figure", match.group(1).split("\n", 1)[0][:120], match.group(1).strip()))
    for match in table_pattern.finditer(text):
        assets.append(ParsedAsset("table", match.group(1).split("\n", 1)[0][:120], match.group(1).strip()))
    return assets


def extract_equation_blocks(text: str) -> list[ParsedAsset]:
    blocks: list[ParsedAsset] = []
    pattern = re.compile(r"(\$\$.+?\$\$|\$.+?\$)", re.DOTALL)
    for index, match in enumerate(pattern.finditer(text), start=1):
        blocks.append(ParsedAsset("equation", f"Equation {index}", match.group(1).strip()))
    return blocks
