# Backend (FastAPI) image.
# Build context is the REPO ROOT (not backend/), because:
#   - backend/main.py uses absolute imports like `from backend.api...`,
#     which requires the repo root to be on sys.path / the working dir.
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY backend/ ./backend/

# Non-root user for the actual FastAPI process - unlike worker/Dockerfile.worker,
# nothing here needs elevated host access, so there's no excuse for root.
#
# One thing this alone does NOT solve: /app/uploads is a bind mount from
# the host (docker-compose.yml's HOST_UPLOADS_DIR), and both the SQLite
# DB file and every uploaded project.zip live there - this user needs
# WRITE access to it. Docker doesn't remap bind-mount ownership to match
# a container user automatically, so `chown -R appuser:appuser /app`
# below only affects the image's own layers, not whatever gets mounted
# over /app/uploads at container start. On the host, either:
#   chmod -R a+rwX <HOST_UPLOADS_DIR>          (simplest, fine for a
#                                                single-tenant deployment)
# or, on a host you don't fully trust with world-writable data:
#   docker compose exec backend id -u          (find this user's UID)
#   chown -R <that UID> <HOST_UPLOADS_DIR>     (match it specifically)
RUN groupadd -r appuser \
    && useradd -r -g appuser -d /home/appuser -s /sbin/nologin -c "Application User" appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# --proxy-headers: without this, Starlette's request.client.host - what
# backend/core/rate_limit.py's Limiter keys on - is always Caddy's own
# container IP in production, not the real client's. Every user behind
# the proxy would then share ONE 5/minute bucket on /auth/login and
# /auth/register, making the rate limit either useless (effectively
# unlimited once averaged across real users) or actively harmful (one
# user's failed logins lock everyone else out). This flag makes uvicorn
# trust X-Forwarded-For and rewrite request.client accordingly.
#
# --forwarded-allow-ips='*': safe specifically because this backend has
# NO direct public exposure in production - docker-compose.prod.yml's
# `ports: !reset []` on this service means Caddy is the only thing that
# can reach it at all, over the internal compose network. If that ever
# changes (backend gets a public port again), this needs to become an
# actual allow-list instead, or a spoofed X-Forwarded-For could bypass
# the rate limit entirely.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
