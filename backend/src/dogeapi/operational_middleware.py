"""Cross-cutting HTTP controls used by every deployment."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

if TYPE_CHECKING:
    from starlette.requests import Request

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class OperationalHeadersMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID and baseline browser security headers."""

    def __init__(self, app: ASGIApp, *, production: bool) -> None:
        super().__init__(app)
        self._production = production

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        supplied_request_id = request.headers.get("x-request-id", "")
        request_id = supplied_request_id if _REQUEST_ID_PATTERN.fullmatch(supplied_request_id) else str(uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        if self._production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


__all__ = ("OperationalHeadersMiddleware",)
