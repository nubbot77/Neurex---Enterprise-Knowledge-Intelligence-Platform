import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Generates a unique request ID per incoming request and adds it to the response headers.
    Reuses a caller-supplied ID when present so traces span services.
    """

    async def dispatch(self, request: Request, call_next):
        # Generate a unique request ID
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()  # Clear any existing context variables

        # Add the request ID to the logger context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        request.state.request_id = (
            request_id  # Store the request ID in the request state for later use
        )
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = (
            request_id  # Add the request ID to the response headers
        )
        return response
