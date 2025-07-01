from fastapi import APIRouter

router = APIRouter()


@router.get("/papers")
async def list_papers() -> dict[str, list]:
    return {"papers": []}
