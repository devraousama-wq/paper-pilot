from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from paperpilot.core.database import SessionLocal
from paperpilot.core.models import PaperRecord

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def library_home(request: Request) -> HTMLResponse:
    async with SessionLocal() as session:
        result = await session.execute(select(PaperRecord).order_by(PaperRecord.id.desc()))
        papers = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "library.html",
        {"papers": papers, "title": "PaperPilot Library"},
    )


@router.get("/papers/{paper_id}", response_class=HTMLResponse)
async def paper_viewer(request: Request, paper_id: int) -> HTMLResponse:
    async with SessionLocal() as session:
        paper = await session.get(PaperRecord, paper_id)
    if not paper:
        return HTMLResponse("<h1>Paper not found</h1>", status_code=404)
    return templates.TemplateResponse(
        request,
        "paper.html",
        {"paper": paper, "title": paper.title},
    )
