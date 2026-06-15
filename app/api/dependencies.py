from typing import cast
from fastapi import Request, Depends

from app.agents.master_agent import MasterAgent
from app.agents.polity_agent import PolityAgent
from app.application.chat_service import ChatService
from app.memory.contracts import MemoryService
from app.rag.retrieval import RetrievalService


def get_memory_service(request: Request) -> MemoryService:
    return cast(MemoryService, request.app.state.memory_service)


def get_retrieval_service(request: Request) -> RetrievalService:
    return cast(RetrievalService, request.app.state.retrieval_service)


def get_chat_service(
    memory_service: MemoryService = Depends(get_memory_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> ChatService:
    master_agent = MasterAgent()
    polity_agent = PolityAgent(
        memory_service=memory_service,
        retrieval_service=retrieval_service,
    )
    return ChatService(
        master_agent=master_agent,
        polity_agent=polity_agent,
    )
