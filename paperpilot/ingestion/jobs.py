from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Coroutine

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from paperpilot.core.models import PaperRecord
from paperpilot.ingestion.sources import (
    ingest_arxiv,
    ingest_doi,
    ingest_pdf,
    result_to_record,
)

logger = structlog.get_logger()


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IngestionJob:
    id: str
    kind: str
    payload: str
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    message: str = ""
    error: str | None = None
    paper_id: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, IngestionJob] = {}
        self._listeners: list[Callable[[IngestionJob], Coroutine[Any, Any, None]]] = []

    def create(self, kind: str, payload: str) -> IngestionJob:
        job = IngestionJob(id=str(uuid.uuid4()), kind=kind, payload=payload)
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> IngestionJob | None:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[IngestionJob]:
        return sorted(self._jobs.values(), key=lambda item: item.created_at, reverse=True)

    async def emit(self, job: IngestionJob) -> None:
        job.updated_at = datetime.now(timezone.utc)
        for listener in self._listeners:
            await listener(job)

    def subscribe(self, listener: Callable[[IngestionJob], Coroutine[Any, Any, None]]) -> None:
        self._listeners.append(listener)

    async def update(
        self,
        job: IngestionJob,
        *,
        status: JobStatus | None = None,
        progress: float | None = None,
        message: str | None = None,
        error: str | None = None,
        paper_id: int | None = None,
    ) -> None:
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = progress
        if message is not None:
            job.message = message
        if error is not None:
            job.error = error
        if paper_id is not None:
            job.paper_id = paper_id
        await self.emit(job)


job_store = JobStore()


async def save_paper(session: AsyncSession, record: dict[str, Any]) -> PaperRecord:
    paper = PaperRecord(
        title=record["title"],
        authors=record["authors"],
        abstract=record["abstract"],
        full_text=record.get("full_text", record["abstract"]),
        checksum=record.get("checksum"),
        doi=record.get("doi"),
        arxiv_id=record.get("arxiv_id"),
        source_path=record.get("source_path"),
        status=record.get("status", "parsed"),
    )
    session.add(paper)
    await session.commit()
    await session.refresh(paper)
    return paper


async def run_ingestion_job(session: AsyncSession, job: IngestionJob) -> None:
    await job_store.update(job, status=JobStatus.RUNNING, progress=0.1, message="starting ingestion")
    try:
        if job.kind == "pdf":
            result = await ingest_pdf(Path(job.payload))
        elif job.kind == "arxiv":
            result = await ingest_arxiv(job.payload)
        elif job.kind == "doi":
            result = await ingest_doi(job.payload)
        else:
            raise ValueError(f"unsupported ingestion kind: {job.kind}")
        await job_store.update(job, progress=0.7, message="saving paper record")
        paper = await save_paper(session, result_to_record(result))
        await job_store.update(
            job,
            status=JobStatus.COMPLETED,
            progress=1.0,
            message="ingestion complete",
            paper_id=paper.id,
        )
        logger.info("ingestion_completed", job_id=job.id, paper_id=paper.id)
    except Exception as exc:
        await job_store.update(
            job,
            status=JobStatus.FAILED,
            progress=1.0,
            message="ingestion failed",
            error=str(exc),
        )
        logger.exception("ingestion_failed", job_id=job.id)


def schedule_ingestion(session_factory: Callable[[], AsyncSession], job: IngestionJob) -> None:
    async def runner() -> None:
        async with session_factory() as session:
            await run_ingestion_job(session, job)

    asyncio.create_task(runner())
