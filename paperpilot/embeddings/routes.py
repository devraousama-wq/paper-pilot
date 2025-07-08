from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from paperpilot.core.database import SessionLocal
from paperpilot.core.models import PaperRecord
from paperpilot.embeddings.indexer import EmbeddingEncoder, FaissIndexStore, chunk_text
from paperpilot.parsers.models import PaperSection

router = APIRouter(prefix="/embeddings", tags=["embeddings"])
encoder = EmbeddingEncoder()
index_store = FaissIndexStore()


class IndexResponse(BaseModel):
    paper_id: int
    chunks_indexed: int


class SearchHit(BaseModel):
    paper_id: int
    section_key: str
    chunk_id: str
    text: str
    score: float


@router.post("/papers/{paper_id}/index", response_model=IndexResponse)
async def index_paper(paper_id: int) -> IndexResponse:
    async with SessionLocal() as session:
        paper = await session.get(PaperRecord, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="paper not found")
        result = await session.execute(
            select(PaperSection).where(PaperSection.paper_id == paper_id)
        )
        sections = result.scalars().all()
    chunks = []
    if sections:
        for section in sections:
            chunks.extend(chunk_text(paper_id, section.section_key, section.content))
    else:
        chunks.extend(chunk_text(paper_id, "abstract", paper.abstract))
        chunks.extend(chunk_text(paper_id, "full_text", paper.full_text))
    texts = [chunk.text for chunk in chunks]
    vectors = encoder.encode(texts) if texts else encoder.encode(["empty"])
    if texts:
        index_store.add(chunks, vectors)
    return IndexResponse(paper_id=paper_id, chunks_indexed=len(chunks))


@router.get("/search", response_model=list[SearchHit])
async def semantic_search(q: str, top_k: int = 10) -> list[SearchHit]:
    vector = encoder.encode([q])[0]
    hits = index_store.search(vector, top_k=top_k)
    return [
        SearchHit(
            paper_id=int(meta["paper_id"]),
            section_key=str(meta["section_key"]),
            chunk_id=str(meta["chunk_id"]),
            text=str(meta["text"]),
            score=score,
        )
        for meta, score in hits
    ]
