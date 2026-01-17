import logging
import os
import secrets
from typing import Optional, Callable, Awaitable

from fastapi import Request, HTTPException, Depends
from itsdangerous import URLSafeSerializer, BadSignature
from sqlmodel import Session

from database import engine, get_session
from models import User

logger = logging.getLogger(__name__)

TENANT_COOKIE = "stf_tenant"
TENANT_COOKIE_MAX_AGE = 60 * 60 * 24 * 30

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(32)
    logger.warning(
        "SECRET_KEY is not set. Generated a temporary key for this process; "
        "set SECRET_KEY to keep sessions stable across restarts."
    )

tenant_serializer = URLSafeSerializer(SECRET_KEY, salt="tenant")

def _sign_tenant(user_id: int) -> str:
    return tenant_serializer.dumps({"user_id": user_id})

def _unsign_tenant(token: str) -> Optional[int]:
    try:
        data = tenant_serializer.loads(token)
    except BadSignature:
        return None
    if isinstance(data, dict):
        user_id = data.get("user_id")
        if isinstance(user_id, int):
            return user_id
    return None

async def attach_tenant(
    request: Request,
    call_next: Callable[[Request], Awaitable],
):
    if request.url.path.startswith("/static"):
        return await call_next(request)

    cookie = request.cookies.get(TENANT_COOKIE)
    cookie_user_id = _unsign_tenant(cookie) if cookie else None
    user_id = None

    with Session(engine) as session:
        user = session.get(User, cookie_user_id) if cookie_user_id else None
        if not user:
            user = User(username=f"tenant_{secrets.token_urlsafe(8)}")
            session.add(user)
            session.commit()
            session.refresh(user)
        user_id = user.id
        request.state.user_id = user_id

    response = await call_next(request)
    if not cookie or cookie_user_id != user_id:
        response.set_cookie(
            TENANT_COOKIE,
            _sign_tenant(user_id),
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
            max_age=TENANT_COOKIE_MAX_AGE,
        )
    return response

def get_current_user(request: Request, session: Session = Depends(get_session)) -> User:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Tenant session missing")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Tenant session invalid")
    return user
