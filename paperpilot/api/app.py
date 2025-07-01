from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from paperpilot.api.routes import router as api_router
from paperpilot.core.database import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="PaperPilot", version="0.1.0")
    app.include_router(api_router, prefix="/api")
    app.mount("/static", StaticFiles(directory="paperpilot/dashboard/static"), name="static")

    @app.on_event("startup")
    async def startup() -> None:
        await init_db()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
