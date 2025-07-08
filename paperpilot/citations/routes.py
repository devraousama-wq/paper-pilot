from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from paperpilot.citations.graph import CitationGraph, parse_references
from paperpilot.core.database import SessionLocal
from paperpilot.core.models import PaperRecord
from paperpilot.parsers.models import PaperSection

router = APIRouter(prefix="/citations", tags=["citations"])
graph = CitationGraph()


class GraphEdge(BaseModel):
    source: int
    target: int


class GraphMetrics(BaseModel):
    paper_id: int
    pagerank: float
    betweenness: float


class NeighborhoodResponse(BaseModel):
    paper_id: int
    incoming: list[int]
    outgoing: list[int]


@router.post("/papers/{paper_id}/build")
async def build_graph_for_paper(paper_id: int) -> dict[str, int | list[int]]:
    async with SessionLocal() as session:
        paper = await session.get(PaperRecord, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="paper not found")
        result = await session.execute(select(PaperRecord))
        library = {}
        for row in result.scalars().all():
            if row.doi:
                library[row.doi] = row.id
            library[row.title.lower()] = row.id
        section_result = await session.execute(
            select(PaperSection).where(
                PaperSection.paper_id == paper_id,
                PaperSection.section_key == "references",
            )
        )
        section = section_result.scalar_one_or_none()
        references = parse_references(section.content if section else paper.full_text)
        graph.add_paper(paper_id, paper.title)
        resolved = graph.resolve_references(paper_id, references, library)
    return {"paper_id": paper_id, "resolved": resolved}


@router.get("/papers/{paper_id}/metrics", response_model=GraphMetrics)
async def paper_metrics(paper_id: int) -> GraphMetrics:
    values = graph.metrics(paper_id)
    return GraphMetrics(paper_id=paper_id, pagerank=values["pagerank"], betweenness=values["betweenness"])


@router.get("/papers/{paper_id}/neighborhood", response_model=NeighborhoodResponse)
async def paper_neighborhood(paper_id: int, depth: int = 1) -> NeighborhoodResponse:
    values = graph.neighborhood(paper_id, depth=depth)
    return NeighborhoodResponse(paper_id=paper_id, incoming=values["incoming"], outgoing=values["outgoing"])


@router.get("/edges", response_model=list[GraphEdge])
async def list_edges() -> list[GraphEdge]:
    return [GraphEdge(source=edge["source"], target=edge["target"]) for edge in graph.export_edges()]
