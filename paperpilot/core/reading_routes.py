from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from paperpilot.core.database import SessionLocal
from paperpilot.core.reading_models import PaperAnnotation, ReadingQueueItem, ReadingStatus

router = APIRouter(prefix="/reading", tags=["reading"])


class QueueRequest(BaseModel):
    paper_id: int
    priority: int = 0


class QueueItemResponse(BaseModel):
    id: int
    paper_id: int
    priority: int
    status: str


class AnnotationRequest(BaseModel):
    paper_id: int
    body: str = ""
    tags: str = ""
    highlight: str = ""


class AnnotationResponse(BaseModel):
    id: int
    paper_id: int
    body: str
    tags: str
    highlight: str


@router.post("/queue", response_model=QueueItemResponse)
async def add_to_queue(request: QueueRequest) -> QueueItemResponse:
    async with SessionLocal() as session:
        item = ReadingQueueItem(paper_id=request.paper_id, priority=request.priority)
        session.add(item)
        await session.commit()
        await session.refresh(item)
    return QueueItemResponse(id=item.id, paper_id=item.paper_id, priority=item.priority, status=item.status)


@router.get("/queue", response_model=list[QueueItemResponse])
async def list_queue() -> list[QueueItemResponse]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(ReadingQueueItem).order_by(ReadingQueueItem.priority.desc(), ReadingQueueItem.id.asc())
        )
        rows = result.scalars().all()
    return [
        QueueItemResponse(id=row.id, paper_id=row.paper_id, priority=row.priority, status=row.status)
        for row in rows
    ]


@router.patch("/queue/{item_id}/status", response_model=QueueItemResponse)
async def update_status(item_id: int, status: ReadingStatus) -> QueueItemResponse:
    async with SessionLocal() as session:
        item = await session.get(ReadingQueueItem, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="queue item not found")
        item.status = status.value
        await session.commit()
        await session.refresh(item)
    return QueueItemResponse(id=item.id, paper_id=item.paper_id, priority=item.priority, status=item.status)


@router.post("/annotations", response_model=AnnotationResponse)
async def create_annotation(request: AnnotationRequest) -> AnnotationResponse:
    async with SessionLocal() as session:
        note = PaperAnnotation(
            paper_id=request.paper_id,
            body=request.body,
            tags=request.tags,
            highlight=request.highlight,
        )
        session.add(note)
        await session.commit()
        await session.refresh(note)
    return AnnotationResponse(
        id=note.id,
        paper_id=note.paper_id,
        body=note.body,
        tags=note.tags,
        highlight=note.highlight,
    )


@router.get("/papers/{paper_id}/export")
async def export_obsidian(paper_id: int) -> dict[str, str]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(PaperAnnotation).where(PaperAnnotation.paper_id == paper_id)
        )
        notes = result.scalars().all()
    lines = [f"# Paper {paper_id}", ""]
    for note in notes:
        tags = " ".join(f"#{part}" for part in note.tags.split(",") if part.strip())
        lines.append(f"## Highlight {note.id} {tags}".strip())
        if note.highlight:
            lines.append(f"> {note.highlight}")
        lines.append(note.body)
        lines.append("")
    return {"markdown": "\n".join(lines)}
