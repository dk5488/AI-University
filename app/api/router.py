from fastapi import APIRouter

from app.api.routes import health, sessions, chat


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(sessions.router)
api_router.include_router(chat.router)
