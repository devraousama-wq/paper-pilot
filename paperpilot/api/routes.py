from fastapi import APIRouter

from paperpilot.citations.routes import router as citations_router
from paperpilot.core.reading_routes import router as reading_router
from paperpilot.embeddings.routes import router as embeddings_router
from paperpilot.ingestion.routes import router as ingestion_router
from paperpilot.ingestion.tools_routes import router as ingestion_tools_router
from paperpilot.parsers.routes import router as parser_router
from paperpilot.rag.routes import router as rag_router
from paperpilot.review.routes import router as review_router
from paperpilot.search.related_routes import router as related_router
from paperpilot.search.routes import router as search_router
from paperpilot.topics.routes import router as topics_router

router = APIRouter()
router.include_router(ingestion_router)
router.include_router(ingestion_tools_router)
router.include_router(parser_router)
router.include_router(embeddings_router)
router.include_router(search_router)
router.include_router(related_router)
router.include_router(rag_router)
router.include_router(citations_router)
router.include_router(review_router)
router.include_router(reading_router)
router.include_router(topics_router)


@router.get("/papers")
async def list_papers() -> dict[str, list]:
    return {"papers": []}
