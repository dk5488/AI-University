from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.memory.in_memory import create_in_memory_memory_service
from app.rag.retrieval import RetrievalService
from app.rag.embeddings import OpenAIEmbeddingClient
from app.infrastructure.vector.qdrant_client import QdrantVectorStore


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Initialize Memory Service
    application.state.memory_service = create_in_memory_memory_service()
    
    # Initialize Retrieval Service
    # Note: In a production environment, we'd use real clients.
    # For now, we'll initialize them with the configured URLs and keys.
    embedding_client = OpenAIEmbeddingClient(api_key=settings.openai_api_key)
    vector_store = QdrantVectorStore(url=settings.qdrant_url)
    
    application.state.retrieval_service = RetrievalService(
        embedding_client=embedding_client,
        vector_store=vector_store,
    )
    
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
