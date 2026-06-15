from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.memory.in_memory import create_in_memory_memory_service


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.state.memory_service = create_in_memory_memory_service()
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    @application.get("/", tags=["root"])
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "ok",
        }

    return application


app = create_app()
