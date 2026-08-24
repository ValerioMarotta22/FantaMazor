from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.security import (
    SESSION_COOKIE_NAME,
    CurrentUser,
    create_session,
    destroy_session,
    verify_password,
)
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, MeResponse

router = APIRouter()


@router.post("/login", response_model=MeResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=payload.username).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    token = create_session(user.username)
    response.set_cookie(SESSION_COOKIE_NAME, token, httponly=True, samesite="lax", max_age=7 * 24 * 3600)
    return MeResponse(username=user.username)


@router.post("/logout")
def logout(response: Response, fm_session: str | None = Cookie(default=None)):
    if fm_session:
        destroy_session(fm_session)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(username: str = CurrentUser):
    return MeResponse(username=username)
