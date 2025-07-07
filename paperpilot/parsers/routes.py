from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from paperpilot.core.database import SessionLocal
from paperpilot.core.models import PaperRecord
from paperpilot.parsers.models import PaperAsset, PaperSection
from paperpilot.parsers.pdf_parser import parse_paper_text

router = APIRouter(prefix="/parsers", tags=["parsers"])


class SectionResponse(BaseModel):
    section_key: str
    title: str
    content: str
    order_index: int


class AssetResponse(BaseModel):
    asset_type: str
    label: str
    content: str


class ParseResponse(BaseModel):
    paper_id: int
    sections: list[SectionResponse]
    assets: list[AssetResponse]


async def persist_sections(session: AsyncSession, paper_id: int, sections, assets) -> None:
    await session.execute(delete(PaperSection).where(PaperSection.paper_id == paper_id))
    await session.execute(delete(PaperAsset).where(PaperAsset.paper_id == paper_id))
    for section in sections:
        session.add(
            PaperSection(
                paper_id=paper_id,
                section_key=section.section_key,
                title=section.title,
                content=section.content,
                order_index=section.order_index,
            )
        )
    for asset in assets:
        session.add(
            PaperAsset(
                paper_id=paper_id,
                asset_type=asset.asset_type,
                label=asset.label,
                content=asset.content,
            )
        )
    await session.commit()


@router.post("/papers/{paper_id}/parse", response_model=ParseResponse)
async def parse_paper_sections(paper_id: int) -> ParseResponse:
    async with SessionLocal() as session:
        paper = await session.get(PaperRecord, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="paper not found")
        full_text = getattr(paper, "full_text", None) or paper.abstract
        sections, assets = parse_paper_text(full_text)
        await persist_sections(session, paper_id, sections, assets)
    return ParseResponse(
        paper_id=paper_id,
        sections=[
            SectionResponse(
                section_key=section.section_key,
                title=section.title,
                content=section.content,
                order_index=section.order_index,
            )
            for section in sections
        ],
        assets=[
            AssetResponse(asset_type=asset.asset_type, label=asset.label, content=asset.content)
            for asset in assets
        ],
    )


@router.get("/papers/{paper_id}/sections", response_model=list[SectionResponse])
async def list_sections(paper_id: int) -> list[SectionResponse]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(PaperSection)
            .where(PaperSection.paper_id == paper_id)
            .order_by(PaperSection.order_index.asc())
        )
        rows = result.scalars().all()
    return [
        SectionResponse(
            section_key=row.section_key,
            title=row.title,
            content=row.content,
            order_index=row.order_index,
        )
        for row in rows
    ]
