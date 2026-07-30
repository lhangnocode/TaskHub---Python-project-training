import logging
import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("taskhub.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request logging, process time calculation, and Request-ID header injection."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response] # type: ignore[override]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.perf_counter()
        logger.info(
            "[%s] HTTP %s %s - Start",
            request_id[:8],
            request.method,
            request.url.path,
        )

        try:
            response = await call_next(request)
            process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = str(process_time_ms)

            logger.info(
                "[%s] HTTP %s %s - %d (%s ms)",
                request_id[:8],
                request.method,
                request.url.path,
                response.status_code,
                process_time_ms,
            )
            return response
        except Exception as exc:
            process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "[%s] HTTP %s %s - FAILED: %s (%s ms)",
                request_id[:8],
                request.method,
                request.url.path,
                exc,
                process_time_ms,
            )
            raise exc
