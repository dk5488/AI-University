import logging
import sys
import time
import uuid
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


def setup_logging() -> None:
    """Sets up basic structured logging to stdout."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        stream=sys.stdout,
    )


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to attach a unique Request-ID to every request and response."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Store request_id in request state for downstream use
        request.state.request_id = request_id
        
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
