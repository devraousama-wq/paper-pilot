from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from paperpilot.review.generator import LiteratureReviewGenerator, ReviewSection

router = APIRouter(prefix="/review", tags=["review"])
generator = LiteratureReviewGenerator()


class ReviewRequest(BaseModel):
    topic: str = Field(min_length=3)
    paper_summaries: list[str] = Field(min_length=1)


class ReviewSectionResponse(BaseModel):
    key: str
    title: str
    content: str


class RegenerateRequest(BaseModel):
    topic: str
    section_key: str
    section_title: str
    paper_summaries: list[str]


@router.post("/generate", response_model=list[ReviewSectionResponse])
async def generate_review(request: ReviewRequest) -> list[ReviewSectionResponse]:
    sections = await generator.generate(request.topic, request.paper_summaries)
    return [
        ReviewSectionResponse(key=section.key, title=section.title, content=section.content)
        for section in sections
    ]


@router.post("/regenerate", response_model=ReviewSectionResponse)
async def regenerate_section(request: RegenerateRequest) -> ReviewSectionResponse:
    section = await generator.regenerate_section(
        request.topic,
        request.section_key,
        request.section_title,
        request.paper_summaries,
    )
    return ReviewSectionResponse(key=section.key, title=section.title, content=section.content)


@router.post("/export")
async def export_review(request: ReviewRequest) -> dict[str, str]:
    sections = await generator.generate(request.topic, request.paper_summaries)
    markdown = generator.export_markdown(request.topic, sections)
    return {"markdown": markdown}
