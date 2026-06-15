from typing import cast
from fastapi import Request, Depends

from app.agents.master_agent import MasterAgent
from app.agents.polity_agent import PolityAgent
from app.application.chat_service import ChatService
from app.application.quiz_service import QuizService
from app.application.revision_service import RevisionService
from app.application.learning_service import LearningService
from app.memory.contracts import MemoryService
from app.rag.retrieval import RetrievalService


def get_memory_service(request: Request) -> MemoryService:
    return cast(MemoryService, request.app.state.memory_service)


def get_retrieval_service(request: Request) -> RetrievalService:
    return cast(RetrievalService, request.app.state.retrieval_service)


def get_quiz_service(
    memory_service: MemoryService = Depends(get_memory_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> QuizService:
    polity_agent = PolityAgent(
        memory_service=memory_service,
        retrieval_service=retrieval_service,
    )
    revision_service = RevisionService(memory_service)
    return QuizService(
        memory_service=memory_service,
        polity_agent=polity_agent,
        revision_service=revision_service,
    )


def get_revision_service(
    memory_service: MemoryService = Depends(get_memory_service),
) -> RevisionService:
    return RevisionService(memory_service)


def get_learning_service(
    memory_service: MemoryService = Depends(get_memory_service),
) -> LearningService:
    return LearningService(memory_service)


def get_chat_service(
    memory_service: MemoryService = Depends(get_memory_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    quiz_service: QuizService = Depends(get_quiz_service),
) -> ChatService:
    master_agent = MasterAgent()
    polity_agent = PolityAgent(
        memory_service=memory_service,
        retrieval_service=retrieval_service,
    )
    return ChatService(
        master_agent=master_agent,
        polity_agent=polity_agent,
        quiz_service=quiz_service,
    )
