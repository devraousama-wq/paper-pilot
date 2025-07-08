from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from paperpilot.core.models import PaperRecord


@dataclass
class DuplicateGroup:
    canonical_id: int
    duplicate_ids: list[int]
    reason: str


def normalize_title(title: str) -> str:
    cleaned = re.sub(r"[^a-z0-9 ]+", "", title.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_authors(authors: str) -> str:
    parts = [part.strip().lower() for part in authors.split(",") if part.strip()]
    return "|".join(sorted(parts))


async def find_duplicates(session: AsyncSession) -> list[DuplicateGroup]:
    result = await session.execute(select(PaperRecord))
    papers = result.scalars().all()
    by_title: dict[str, list[PaperRecord]] = {}
    by_doi: dict[str, list[PaperRecord]] = {}
    by_authors_title: dict[str, list[PaperRecord]] = {}
    for paper in papers:
        title_key = normalize_title(paper.title)
        by_title.setdefault(title_key, []).append(paper)
        if paper.doi:
            by_doi.setdefault(paper.doi.lower(), []).append(paper)
        combo = f"{normalize_authors(paper.authors)}::{title_key}"
        by_authors_title.setdefault(combo, []).append(paper)
    groups: list[DuplicateGroup] = []
    seen: set[int] = set()

    def add_group(items: list[PaperRecord], reason: str) -> None:
        if len(items) < 2:
            return
        canonical = min(paper.id for paper in items)
        duplicates = [paper.id for paper in items if paper.id != canonical]
        if not duplicates:
            return
        if canonical in seen:
            return
        seen.add(canonical)
        groups.append(DuplicateGroup(canonical_id=canonical, duplicate_ids=duplicates, reason=reason))

    for items in by_doi.values():
        add_group(items, "doi")
    for items in by_title.values():
        add_group(items, "title")
    for items in by_authors_title.values():
        add_group(items, "title+author")
    return groups


async def dismiss_duplicate(session: AsyncSession, paper_id: int) -> None:
    paper = await session.get(PaperRecord, paper_id)
    if paper:
        paper.status = "duplicate"
        await session.commit()
