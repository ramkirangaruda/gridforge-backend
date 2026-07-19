import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from backend.api.endpoints import router as api_router
from backend.core.config import settings
from backend.core.logging import setup_logging
from backend.core.rate_limit import limiter

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

# Registers the limiter so @limiter.limit(...) decorators in endpoints.py
# work, and translates a hit limit into a 429 response instead of an
# unhandled RateLimitExceeded exception.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Rejects a request whose declared Content-Length exceeds the cap
    before Starlette parses the body at all - the cheapest possible
    rejection point, and the only one that runs before any of the request
    is read into memory or spooled to disk.

    This only helps when the client sends an honest Content-Length, which
    is true for our own frontend (a real File object in a FormData body
    always has a known length) but isn't guaranteed for chunked-encoding
    or malicious clients - submit_project() in api/endpoints.py re-checks
    the actual received size via UploadFile.size as the authoritative
    fallback, since that one can't be bypassed by lying about the header.
    """

    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = None
            if declared_size is not None and declared_size > self.max_bytes:
                logger.warning(
                    f"Rejecting request to {request.url.path}: "
                    f"Content-Length {declared_size} exceeds {self.max_bytes} bytes."
                )
                return JSONResponse(
                    {"detail": f"Request body exceeds the {self.max_bytes} byte limit."},
                    status_code=413,
                )
        return await call_next(request)


app.add_middleware(MaxBodySizeMiddleware, max_bytes=settings.MAX_UPLOAD_SIZE_BYTES)

# FRONTEND_URL may be a single origin or a comma-separated list (e.g. a
# custom domain plus a Vercel preview URL). Wildcard CORS on an API that
# accepts a bearer token is a real hole - even though the token isn't
# cookie-based (no CSRF risk), it makes token-leaking XSS on *any* site
# easier to exploit against this API. Outside of ENVIRONMENT=development,
# refuse to start rather than silently falling back to "*": a missing env
# var should be a loud deploy failure, not a quiet security regression
# that only shows up later as "huh, why is this API open to every origin."
if not settings.FRONTEND_URL:
    if settings.ENVIRONMENT != "development":
        raise RuntimeError(
            "FRONTEND_URL is not set and ENVIRONMENT is not 'development' "
            f"(got {settings.ENVIRONMENT!r}). Refusing to start with wildcard "
            "CORS on an API that accepts a bearer token - set FRONTEND_URL in "
            "the environment/.env to your frontend's origin(s), comma-separated."
        )
    logger.warning("FRONTEND_URL not set - falling back to CORS allow_origins=['*']. This is only allowed because ENVIRONMENT=development.")

origins = [origin.strip() for origin in settings.FRONTEND_URL.split(",")] if settings.FRONTEND_URL else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"message": "Welcome to GridForge API"}


@app.get("/health")
def health():
    """
    Used by docker-compose's healthcheck (see the backend service there)
    to gate worker's `depends_on: condition: service_healthy` - the
    container-started signal that condition replaces only confirms the
    process launched, not that uvicorn is actually accepting connections
    yet. Deliberately just confirms the ASGI app itself is up and routing
    - no DB/Redis check here, so a brief Redis blip doesn't also flip the
    backend container to "unhealthy" and potentially get it restarted for
    an unrelated dependency's problem.
    """
    return {"status": "ok"}
