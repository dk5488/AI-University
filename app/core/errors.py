from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all application errors."""
    def __init__(self, message: str, code: str = "internal_error", details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class DomainError(AppError):
    """Errors related to domain business rules."""
    pass


class InfrastructureError(AppError):
    """Errors related to external infrastructure (DB, LLM, etc.)."""
    pass


class NotFoundError(DomainError):
    """Requested resource not found."""
    def __init__(self, resource: str, identifier: Any) -> None:
        super().__init__(
            message=f"{resource} with identifier {identifier} not found",
            code="not_found",
            details={"resource": resource, "identifier": identifier}
        )


class LlmUnavailableError(InfrastructureError):
    """LLM service is unreachable or failed."""
    def __init__(self, message: str = "LLM service is currently unavailable") -> None:
        super().__init__(message=message, code="llm_unavailable")


class RetrievalUnavailableError(InfrastructureError):
    """Vector store or retrieval service failed."""
    def __init__(self, message: str = "Retrieval service is currently unavailable") -> None:
        super().__init__(message=message, code="retrieval_unavailable")
