import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.observability import tag_request

logger = logging.getLogger("maf.request")

REQUEST_ID_HEADER = "X-Request-ID"

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # The clock-in check needs the browser's own location, and nothing else needs a device.
    "Permissions-Policy": "geolocation=(self), camera=(), microphone=(), payment=()",
}


def harden(response: Response, request_id: str) -> Response:
    """Stamp a response with the request id and the security headers.

    Applied in two places because the catch-all 500 handler runs in Starlette's
    ServerErrorMiddleware, which sits outside this middleware — its response never comes back
    through, so without this a crash is the one reply with no id and no headers on it.
    """
    response.headers[REQUEST_ID_HEADER] = request_id
    response.headers.update(SECURITY_HEADERS)
    if settings.environment != "development":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def observe_and_harden(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        tag_request(request_id)
        started = time.perf_counter()

        response = await call_next(request)

        harden(response, request_id)

        logger.info(
            "%s %s %s %.0fms",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
            extra={"request_id": request_id},
        )
        return response

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Keeps every error the same shape, including the ones Starlette raises itself (404, 405)."""
        detail = exc.detail
        body = (
            detail if isinstance(detail, dict) else {"code": _slug(exc.status_code), "message": str(detail)}
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": body})

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "invalid_request",
                    "message": "Check the details and try again.",
                    "fields": [".".join(str(part) for part in error["loc"][1:]) for error in exc.errors()],
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """A crash must not leak a stack trace to the caller; the request id ties it to the log."""
        request_id = getattr(request.state, "request_id", "unknown")
        # This log line is also what reports the crash to Sentry, tagged with the request id.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return harden(
            JSONResponse(
                status_code=500,
                content={
                    "detail": {
                        "code": "server_error",
                        "message": "Something went wrong at our end. Try again.",
                        "request_id": request_id,
                    }
                },
            ),
            request_id,
        )


def _slug(status_code: int) -> str:
    return {401: "not_authenticated", 403: "forbidden", 404: "not_found", 405: "method_not_allowed"}.get(
        status_code, "error"
    )
