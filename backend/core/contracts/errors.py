from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ErrorModel(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)
    request_id: str | None = None
    trace_id: str | None = None
    retryable: bool = False
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApiError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: list[dict[str, Any]] | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error = ErrorModel(
            code=code,
            message=message,
            details=details or [],
            request_id=request_id,
            trace_id=trace_id,
            retryable=retryable,
        )


__all__ = ["ApiError", "ErrorModel"]
