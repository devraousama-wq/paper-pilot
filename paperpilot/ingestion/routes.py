from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from paperpilot.core.database import SessionLocal
from paperpilot.core.models import PaperRecord
from paperpilot.ingestion.jobs import job_store, schedule_ingestion
from paperpilot.ingestion.sources import parse_arxiv_id, parse_doi

logger = structlog.get_logger()
router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class ArxivRequest(BaseModel):
    identifier: str = Field(min_length=3)


class DoiRequest(BaseModel):
    identifier: str = Field(min_length=5)


class JobResponse(BaseModel):
    id: str
    kind: str
    status: str
    progress: float
    message: str
    error: str | None = None
    paper_id: int | None = None


class PaperResponse(BaseModel):
    id: int
    title: str
    authors: str
    abstract: str
    doi: str | None
    arxiv_id: str | None
    status: str


def job_to_response(job) -> JobResponse:
    return JobResponse(
        id=job.id,
        kind=job.kind,
        status=job.status,
        progress=job.progress,
        message=job.message,
        error=job.error,
        paper_id=job.paper_id,
    )


@router.post("/upload", response_model=JobResponse)
async def upload_pdf(file: UploadFile = File(...)) -> JobResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="pdf file required")
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / file.filename
    content = await file.read()
    target.write_bytes(content)
    job = job_store.create("pdf", str(target))
    schedule_ingestion(SessionLocal, job)
    return job_to_response(job)


@router.post("/arxiv", response_model=JobResponse)
async def ingest_from_arxiv(request: ArxivRequest) -> JobResponse:
    if not parse_arxiv_id(request.identifier):
        raise HTTPException(status_code=400, detail="invalid arxiv identifier")
    job = job_store.create("arxiv", request.identifier)
    schedule_ingestion(SessionLocal, job)
    return job_to_response(job)


@router.post("/doi", response_model=JobResponse)
async def ingest_from_doi(request: DoiRequest) -> JobResponse:
    if not parse_doi(request.identifier):
        raise HTTPException(status_code=400, detail="invalid doi")
    job = job_store.create("doi", request.identifier)
    schedule_ingestion(SessionLocal, job)
    return job_to_response(job)


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs() -> list[JobResponse]:
    return [job_to_response(job) for job in job_store.list_jobs()]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job_to_response(job)


@router.get("/papers", response_model=list[PaperResponse])
async def list_ingested_papers() -> list[PaperResponse]:
    async with SessionLocal() as session:
        result = await session.execute(select(PaperRecord).order_by(PaperRecord.id.desc()))
        papers = result.scalars().all()
    return [
        PaperResponse(
            id=paper.id,
            title=paper.title,
            authors=paper.authors,
            abstract=paper.abstract,
            doi=paper.doi,
            arxiv_id=paper.arxiv_id,
            status=paper.status,
        )
        for paper in papers
    ]
