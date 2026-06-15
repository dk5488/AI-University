from typing import cast

from fastapi import Request

from app.memory.contracts import MemoryService


def get_memory_service(request: Request) -> MemoryService:
    return cast(MemoryService, request.app.state.memory_service)
