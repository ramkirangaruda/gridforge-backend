import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.endpoints import router as api_router
from backend.core.config import settings
from backend.core.logging import setup_logging

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

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
