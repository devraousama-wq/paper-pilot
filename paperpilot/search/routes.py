from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from paperpilot.search.hybrid import HybridSearchEngine, SearchFilters

router = APIRouter(prefix="/search", tags=["search"])
engine = HybridSearchEngine()


class SearchResult(BaseModel):
    paper_id: int
    title: str
    snippet: str
    score: float
    authors: str
    year: int | None = None


class RegisterRequest(BaseModel):
    paper_id: int
    title: str
    text: str
    authors: str
    year: int | None = None


@router.post("/register")
async def register_document(request: RegisterRequest) -> dict[str, str]:
    engine.register_document(
        request.paper_id,
        request.title,
        request.text,
        request.authors,
        request.year,
    )
    return {"status": "registered"}


@router.get("/query", response_model=list[SearchResult])
async def search_library(
    q: str = Query(min_length=2),
    year: int | None = None,
    author: str | None = None,
    venue: str | None = None,
    top_k: int = 10,
) -> list[SearchResult]:
    hits = engine.search(
        q,
        filters=SearchFilters(year=year, author=author, venue=venue),
        top_k=top_k,
    )
    return [
        SearchResult(
            paper_id=hit.paper_id,
            title=hit.title,
            snippet=hit.snippet,
            score=hit.score,
            authors=hit.authors,
            year=hit.year,
        )
        for hit in hits
    ]
