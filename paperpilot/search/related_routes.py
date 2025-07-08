from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from paperpilot.search.related import RelatedPaper, RelatedWorkEngine

router = APIRouter(prefix="/related", tags=["related"])
engine = RelatedWorkEngine()


class RegisterPaperRequest(BaseModel):
    paper_id: int
    title: str
    authors: str
    text: str


class RelatedPaperResponse(BaseModel):
    paper_id: int
    title: str
    score: float
    reasons: list[str]


@router.post("/register")
async def register_paper(request: RegisterPaperRequest) -> dict[str, str]:
    engine.register_paper(request.paper_id, request.title, request.authors, request.text)
    return {"status": "registered"}


@router.get("/papers/{paper_id}", response_model=list[RelatedPaperResponse])
async def suggest_related(paper_id: int, top_k: int = 8) -> list[RelatedPaperResponse]:
    hits: list[RelatedPaper] = engine.suggest(paper_id, top_k=top_k)
    if not hits and paper_id not in engine.library:
        raise HTTPException(status_code=404, detail="paper not registered")
    return [
        RelatedPaperResponse(
            paper_id=hit.paper_id,
            title=hit.title,
            score=hit.score,
            reasons=hit.reasons,
        )
        for hit in hits
    ]
