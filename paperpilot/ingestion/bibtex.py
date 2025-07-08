from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class BibEntry:
    key: str
    title: str
    authors: list[str]
    year: int | None
    doi: str | None
    arxiv_id: str | None


ENTRY_PATTERN = re.compile(r"@(\w+)\s*\{\s*([^,]+),", re.MULTILINE)
FIELD_PATTERN = re.compile(r"(\w+)\s*=\s*[{"](.+?)[}]", re.DOTALL)


def parse_bibtex(content: str) -> list[BibEntry]:
    entries: list[BibEntry] = []
    for match in ENTRY_PATTERN.finditer(content):
        key = match.group(2).strip()
        start = match.end()
        end = content.find("\n@", start)
        block = content[start:end if end >= 0 else len(content)]
        fields = {name.lower(): value.strip() for name, value in FIELD_PATTERN.findall(block)}
        authors = [part.strip() for part in fields.get("author", "").split(" and ") if part.strip()]
        year = int(fields["year"]) if fields.get("year", "").isdigit() else None
        doi = fields.get("doi")
        arxiv_id = fields.get("eprint") or fields.get("arxiv")
        entries.append(
            BibEntry(
                key=key,
                title=fields.get("title", key).strip("{}"),
                authors=authors,
                year=year,
                doi=doi,
                arxiv_id=arxiv_id,
            )
        )
    return entries


class MetadataCache:
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", key)
        return self.cache_dir / f"{safe}.json"

    def get(self, key: str) -> dict | None:
        path = self._path(key)
        if not path.exists():
            return None
        import json

        return json.loads(path.read_text(encoding="utf-8"))

    def set(self, key: str, payload: dict) -> None:
        import json

        self._path(key).write_text(json.dumps(payload), encoding="utf-8")


async def enrich_openalex(doi: str | None, cache: MetadataCache) -> dict | None:
    if not doi:
        return None
    cached = cache.get(doi)
    if cached:
        return cached
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        if response.status_code >= 400:
            return None
        payload = response.json()
    cache.set(doi, payload)
    return payload
