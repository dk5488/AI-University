from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging, RequestIdMiddleware
from app.core.errors import AppError, DomainError
from app.memory.in_memory import create_in_memory_memory_service
from app.rag.retrieval import RetrievalService
from app.rag.embeddings import OpenAIEmbeddingClient
from app.infrastructure.vector.qdrant_client import QdrantVectorStore

def create_app() -> FastAPI:
    settings = get_settings()

    # Initialize Logging
    setup_logging()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add Middleware
    application.add_middleware(RequestIdMiddleware)

    # Exception Handlers
    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=400 if isinstance(exc, DomainError) else 500,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": getattr(request.state, "request_id", None)
                }
            },
        )

    # Initialize Memory Service
    application.state.memory_service = create_in_memory_memory_service()
    
    # Initialize Retrieval Service

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
