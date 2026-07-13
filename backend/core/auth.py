import logging
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Just extracts a Bearer token from the Authorization header (and gives us
# the Swagger "Authorize" button) - this is FastAPI's plain-JWT pattern, not
# a full OAuth2 provider flow.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_token(token: Optional[str]) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise credentials_exception

    username = payload.get("sub")
    if not username:
        raise credentials_exception
    return username


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Route dependency: decodes the `Authorization: Bearer` JWT and
    returns the username.

    Raises 401 for any missing/malformed/expired/invalid-signature token.
    Trusts the signed token rather than re-checking the user still exists
    in the DB on every request - acceptable for this project's scope, but
    means a deleted user's existing tokens stay valid until they expire.
    """
    return _decode_token(token)


def get_current_user_sse(token: Optional[str] = Query(default=None)) -> str:
    """Same as get_current_user, but reads the JWT from a `?token=` query
    param instead of the Authorization header.

    Only for the SSE stream endpoint: browsers' EventSource API can't set
    custom request headers, so the token has to travel in the URL instead.
    Downside is the token can end up in server access logs / browser
    history - acceptable tradeoff for this project's scope, but worth
    knowing if this pattern gets reused somewhere more sensitive.
    """
    return _decode_token(token)


def verify_worker_key(x_worker_key: Optional[str] = Header(default=None)) -> None:
    """Route dependency guarding the worker-only status-update endpoint.

    The worker process has no user identity to put in a JWT, so it
    authenticates with a static shared secret instead (WORKER_API_KEY,
    same value in both backend and worker config/.env).
    """
    if not x_worker_key or x_worker_key != settings.WORKER_API_KEY:
        logger.warning("Rejected /task update request with invalid or missing worker key.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid worker API key")
