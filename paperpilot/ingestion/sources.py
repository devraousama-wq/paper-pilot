from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import structlog
from pypdf import PdfReader

from paperpilot.core.config import settings

logger = structlog.get_logger()


@dataclass
class PaperMetadata:
    title: str
    authors: list[str]
    abstract: str = ""
    doi: str | None = None
    arxiv_id: str | None = None
    year: int | None = None
    venue: str | None = None


@dataclass
class IngestionResult:
    metadata: PaperMetadata
    full_text: str
    source: str
    checksum: str


def checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_arxiv_id(value: str) -> str | None:
    cleaned = value.strip()
    patterns = [
        r"arxiv\.org/abs/([\d.]+)",
        r"arxiv:([\d.]+)",
        r"^([\d]{4}\.[\d]{4,5})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def parse_doi(value: str) -> str | None:
    match = re.search(r"(10\.\d{4,9}/\S+)", value.strip(), re.IGNORECASE)
    if match:
        return match.group(1).rstrip(".,)")
    return None


async def fetch_arxiv_metadata(arxiv_id: str) -> PaperMetadata:
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        xml = response.text
    title_match = re.search(r"<title>(.*?)</title>", xml, re.DOTALL)
    summary_match = re.search(r"<summary>(.*?)</summary>", xml, re.DOTALL)
    author_matches = re.findall(r"<name>(.*?)</name>", xml)
    title = title_match.group(1).strip().replace("\n", " ") if title_match else arxiv_id
    abstract = summary_match.group(1).strip().replace("\n", " ") if summary_match else ""
    authors = [name.strip() for name in author_matches if name.strip().lower() != "title"]
    return PaperMetadata(title=title, authors=authors, abstract=abstract, arxiv_id=arxiv_id)


async def fetch_doi_metadata(doi: str) -> PaperMetadata:
    url = f"https://api.crossref.org/works/{doi}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()["message"]
    title_parts = payload.get("title") or [doi]
    authors = []
    for item in payload.get("author") or []:
        given = item.get("given") or ""
        family = item.get("family") or ""
        name = f"{given} {family}".strip()
        if name:
            authors.append(name)
    year = None
    issued = payload.get("issued", {}).get("date-parts")
    if issued and issued[0]:
        year = int(issued[0][0])
    venue = None
    container = payload.get("container-title") or []
    if container:
        venue = container[0]
    return PaperMetadata(
        title=title_parts[0],
        authors=authors,
        abstract=(payload.get("abstract") or "").replace("<jats:p>", "").replace("</jats:p>", ""),
        doi=doi,
        year=year,
        venue=venue,
    )


def extract_pdf_text(path: Path) -> tuple[str, PaperMetadata]:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    full_text = "\n".join(pages).strip()
    metadata = reader.metadata or {}
    title = str(metadata.get("/Title") or path.stem)
    author = str(metadata.get("/Author") or "")
    authors = [part.strip() for part in author.split(",") if part.strip()]
    return full_text, PaperMetadata(title=title, authors=authors)


async def ingest_pdf(path: Path) -> IngestionResult:
    data = path.read_bytes()
    full_text, metadata = extract_pdf_text(path)
    return IngestionResult(
        metadata=metadata,
        full_text=full_text,
        source=str(path),
        checksum=checksum_bytes(data),
    )


async def ingest_arxiv(value: str) -> IngestionResult:
    arxiv_id = parse_arxiv_id(value)
    if not arxiv_id:
        raise ValueError("invalid arxiv identifier")
    metadata = await fetch_arxiv_metadata(arxiv_id)
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(pdf_url)
        response.raise_for_status()
        data = response.content
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"{arxiv_id.replace('/', '_')}.pdf"
    target.write_bytes(data)
    full_text, pdf_meta = extract_pdf_text(target)
    if pdf_meta.title and pdf_meta.title != target.stem:
        metadata.title = pdf_meta.title
    if pdf_meta.authors:
        metadata.authors = pdf_meta.authors
    return IngestionResult(
        metadata=metadata,
        full_text=full_text,
        source=str(target),
        checksum=checksum_bytes(data),
    )


async def ingest_doi(value: str) -> IngestionResult:
    doi = parse_doi(value)
    if not doi:
        raise ValueError("invalid doi")
    metadata = await fetch_doi_metadata(doi)
    return IngestionResult(
        metadata=metadata,
        full_text=metadata.abstract,
        source=f"doi:{doi}",
        checksum=checksum_bytes(doi.encode("utf-8")),
    )


def result_to_record(result: IngestionResult) -> dict[str, Any]:
    return {
        "title": result.metadata.title,
        "authors": ", ".join(result.metadata.authors),
        "abstract": result.metadata.abstract,
        "doi": result.metadata.doi,
        "arxiv_id": result.metadata.arxiv_id,
        "source_path": result.source,
        "status": "parsed",
        "full_text": result.full_text,
        "checksum": result.checksum,
    }
