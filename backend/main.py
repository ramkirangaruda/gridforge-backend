import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from backend.api.endpoints import router as api_router
from backend.core.config import settings
from backend.core.logging import setup_logging

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)


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
# custom domain plus a Vercel preview URL). Falls back to "*" only when
# unset, which is fine for local dev but must never happen in production -
# wildcard CORS on an API that accepts a bearer token is a real hole, even
# though the token isn't cookie-based (no CSRF risk), because it makes
# token-leaking XSS on *any* site easier to exploit against this API.
if settings.FRONTEND_URL:
    origins = [origin.strip() for origin in settings.FRONTEND_URL.split(",")]
else:
    logger.warning("FRONTEND_URL not set - falling back to CORS allow_origins=['*']. Set it in production.")
    origins = ["*"]

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
