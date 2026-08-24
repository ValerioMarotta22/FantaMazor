"""Single-admin session auth for MVP1.

There is exactly one login (the commissioner). Sessions are opaque tokens
stored server-side in Redis (not JWTs — nothing here needs to be stateless),
delivered to the browser as an HttpOnly cookie. This is intentionally the
simplest thing that works; multi-user league accounts are a later phase and
will replace this module rather than extend it.
"""

import secrets
from datetime import timedelta

import bcrypt
from fastapi import Cookie, Depends, HTTPException, status

from app.core.cache import get_redis

SESSION_COOKIE_NAME = "fm_session"
SESSION_TTL = timedelta(days=7)

# bcrypt truncates at 72 bytes -- fine for MVP1's single admin password.
_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    truncated = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    truncated = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.checkpw(truncated, password_hash.encode("utf-8"))


def create_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    redis = get_redis()
    redis.setex(f"session:{token}", int(SESSION_TTL.total_seconds()), username)
    return token


def destroy_session(token: str) -> None:
    get_redis().delete(f"session:{token}")


def get_current_username(fm_session: str | None = Cookie(default=None)) -> str:
    if not fm_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    redis = get_redis()
    username = redis.get(f"session:{fm_session}")
    if not username:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    return username.decode() if isinstance(username, bytes) else username


CurrentUser = Depends(get_current_username)
