from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_chat_service
from app.application.chat_service import ChatService


router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    user_id: UUID
    message: str = Field(..., min_length=1)
    session_id: str | None = None


class SourceResponse(BaseModel):
    title: str
    chapter: str | None
    page_start: int | None


class ChatResponse(BaseModel):
    answer: str
    subject: str
    topic: str | None
    sources: list[SourceResponse]
    next_actions: list[str] = Field(default_factory=list)


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    result = await chat_service.chat(
        user_id=request.user_id,
        message=request.message,
        session_id=request.session_id,
    )
    
    # Ensure next_actions is present as per contract
    if "next_actions" not in result:
        result["next_actions"] = []
        
    return result
