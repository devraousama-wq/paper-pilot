from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from paperpilot.core.database import SessionLocal
from paperpilot.core.models import PaperRecord
from paperpilot.ingestion.bibtex import MetadataCache, enrich_openalex, parse_bibtex
from paperpilot.ingestion.dedup import dismiss_duplicate, find_duplicates
from paperpilot.ingestion.recovery import recovery_store, retry_failed_jobs

router = APIRouter(prefix="/ingestion-tools", tags=["ingestion-tools"])


class DuplicateGroupResponse(BaseModel):
    canonical_id: int
    duplicate_ids: list[int]
    reason: str


@router.post("/bibtex/import")
async def import_bibtex(file: UploadFile = File(...)) -> dict[str, int | list[str]]:
    content = (await file.read()).decode("utf-8", errors="ignore")
    entries = parse_bibtex(content)
    cache = MetadataCache(Path("data/cache"))
    imported: list[str] = []
    async with SessionLocal() as session:
        for entry in entries:
            await enrich_openalex(entry.doi, cache)
            paper = PaperRecord(
                title=entry.title,
                authors=", ".join(entry.authors),
                doi=entry.doi,
                arxiv_id=entry.arxiv_id,
                status="imported",
            )
            session.add(paper)
            imported.append(entry.key)
        await session.commit()
    return {"count": len(imported), "keys": imported}


@router.get("/dedup", response_model=list[DuplicateGroupResponse])
async def list_duplicates() -> list[DuplicateGroupResponse]:
    async with SessionLocal() as session:
        groups = await find_duplicates(session)
    return [
        DuplicateGroupResponse(
            canonical_id=group.canonical_id,
            duplicate_ids=group.duplicate_ids,
            reason=group.reason,
        )
        for group in groups
    ]


@router.post("/dedup/{paper_id}/dismiss")
async def dismiss_paper_duplicate(paper_id: int) -> dict[str, str]:
    async with SessionLocal() as session:
        await dismiss_duplicate(session, paper_id)
    return {"status": "dismissed"}


@router.post("/jobs/retry")
async def retry_jobs() -> dict[str, list[str]]:
    retried = await retry_failed_jobs()
    recovery_store.persist()
    return {"retried": retried}
