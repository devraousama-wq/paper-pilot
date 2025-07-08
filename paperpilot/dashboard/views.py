from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter(tags=["dashboard-views"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@router.get("/chat", response_class=HTMLResponse)
async def chat_view(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "chat.html", {"title": "RAG Chat"})


@router.get("/graph", response_class=HTMLResponse)
async def graph_view(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "graph.html", {"title": "Citation Graph"})


@router.get("/review", response_class=HTMLResponse)
async def review_view(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "review.html", {"title": "Literature Review"})


@router.get("/topics", response_class=HTMLResponse)
async def topics_view(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "topics.html", {"title": "Topic Explorer"})


@router.get("/queue", response_class=HTMLResponse)
async def queue_view(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "queue.html", {"title": "Reading Queue"})
