import logging
import sys
import time
import uuid
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Sets up basic structured logging to stdout."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to attach a unique Request-ID to every request and response."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Store request_id in request state for downstream use
        request.state.request_id = request_id
        
        start_time = time.perf_counter()
        logger.info(
            "request_start request_id=%s method=%s path=%s client=%s",
            request_id,
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown",
        )
        try:
            response = await call_next(request)
        except Exception:
            process_time = time.perf_counter() - start_time
            logger.exception(
                "request_failed request_id=%s method=%s path=%s duration_ms=%.2f",
                request_id,
                request.method,
                request.url.path,
                process_time * 1000,
            )
            raise
        process_time = time.perf_counter() - start_time
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        logger.info(
            "request_end request_id=%s method=%s path=%s status_code=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            process_time * 1000,
        )
        
        return response
