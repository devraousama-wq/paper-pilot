from fastapi import APIRouter

from paperpilot.ingestion.routes import router as ingestion_router

router = APIRouter()
router.include_router(ingestion_router)


@router.get("/papers")
async def list_papers() -> dict[str, list]:
    return {"papers": []}
