import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging, RequestIdMiddleware
from app.core.errors import AppError, DomainError
from app.memory.in_memory import create_in_memory_memory_service
from app.rag.retrieval import RetrievalService
from app.rag.embeddings import GeminiEmbeddingClient
from app.rag.rag_pipeline_client import RagPipelineClient
from app.infrastructure.vector.qdrant_client import QdrantVectorStore
from app.application.curriculum_service import CurriculumService

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    # Initialize Logging
    setup_logging()
    logger.info(
        "app_start name=%s version=%s environment=%s gemini_key_configured=%s qdrant_url=%s",
        settings.app_name,
        settings.app_version,
        settings.environment,
        bool(settings.gemini_api_key),
        settings.qdrant_url,
    )

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add middleware. CORS must wrap request logging so 500 responses still
    # include browser-visible CORS headers.
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    @application.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.exception(
            "unhandled_request_error method=%s path=%s request_id=%s",
            request.method,
            request.url.path,
            getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "Internal server error",
                    "details": {},
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    # Initialize Memory Service
    application.state.memory_service = create_in_memory_memory_service()
    logger.info("memory_service_initialized backend=in_memory")
    
    # Initialize Retrieval Service

    # For now, we'll initialize them with the configured URLs and keys.
    embedding_client = GeminiEmbeddingClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_embedding_model,
        output_dimensionality=settings.gemini_embedding_dimensions,
    )
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        vector_size=settings.gemini_embedding_dimensions,
    )
    
    application.state.retrieval_service = RetrievalService(
        embedding_client=embedding_client,
        vector_store=vector_store,
    )
    logger.info("retrieval_service_initialized embedding_model=%s", settings.gemini_embedding_model)

    # Initialize RAG Pipeline Client (calls RAG Pipeline HTTP API for teaching queries)
    application.state.rag_pipeline_client = RagPipelineClient(
        base_url=settings.rag_pipeline_url,
    )
    logger.info("rag_pipeline_client_initialized url=%s", settings.rag_pipeline_url)

    # Initialize Curriculum Service
    curriculum_service = CurriculumService(
        memory_service=application.state.memory_service,
        model=settings.gemini_chat_model,
        api_key=settings.gemini_api_key,
    )
    application.state.curriculum_service = curriculum_service
    logger.info("curriculum_service_initialized model=%s", settings.gemini_chat_model)

    # Startup event: ensure Polity curriculum is loaded
    async def load_curriculum_background() -> None:
        try:
            nodes = await curriculum_service.ensure_curriculum("polity")
            logger.info("curriculum_background_complete subject=polity node_count=%d", len(nodes))
        except Exception:
            logger.exception("curriculum_background_failed subject=polity will_retry_on_first_request=true")

    @application.on_event("startup")
    async def load_curriculum():
        asyncio.create_task(load_curriculum_background())
        logger.info("curriculum_background_scheduled subject=polity")
    
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
