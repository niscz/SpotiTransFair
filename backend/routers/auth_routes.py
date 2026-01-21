from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import get_session
from models import User, Connection, Provider
from auth import get_spotify_auth_url, get_tidal_auth_url, exchange_spotify_code, exchange_tidal_code
from qobuz import login_qobuz, QobuzError
import ytm
import secrets
from itsdangerous import URLSafeSerializer, BadSignature
import logging
from tenant import SECRET_KEY, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

serializer = URLSafeSerializer(SECRET_KEY, salt="oauth-state")

@router.get("/connect")
def connect_page(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    conns = session.exec(select(Connection).where(Connection.user_id == user.id)).all()
    conn_map = {c.provider: True for c in conns}

    return templates.TemplateResponse("connect.html", {
        "request": request,
        "spotify_connected": conn_map.get(Provider.SPOTIFY, False),
        "tidal_connected": conn_map.get(Provider.TIDAL, False),
        "ytm_connected": conn_map.get(Provider.YTM, False),
        "qobuz_connected": conn_map.get(Provider.QOBUZ, False),
    })

@router.get("/auth/{provider}/login")
def login(provider: Provider) -> Response:
    state = secrets.token_urlsafe(16)
    url = "/"
    if provider == Provider.SPOTIFY:
        url = get_spotify_auth_url(state)
    elif provider == Provider.TIDAL:
        url = get_tidal_auth_url(state)

    response = RedirectResponse(url)
    # Sign the state to verify it later
    signed_state = serializer.dumps(state)
    response.set_cookie(key="oauth_state", value=signed_state, httponly=True, max_age=600)
    return response

@router.get("/callback/{provider}")
def callback(
    provider: Provider,
    code: str,
    state: str,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:

    # Helper to get status
    conns = session.exec(select(Connection).where(Connection.user_id == user.id)).all()
    conn_map = {c.provider: True for c in conns}
    status = {
        "spotify_connected": conn_map.get(Provider.SPOTIFY, False),
        "tidal_connected": conn_map.get(Provider.TIDAL, False),
        "ytm_connected": conn_map.get(Provider.YTM, False),
        "qobuz_connected": conn_map.get(Provider.QOBUZ, False),
    }

    try:
        # Verify state
        cookie_state = request.cookies.get("oauth_state")
        if not cookie_state:
            raise ValueError("State cookie missing. Please try again.")

        try:
            original_state = serializer.loads(cookie_state)
            if not secrets.compare_digest(original_state, state):
                raise ValueError("State mismatch. Possible CSRF attack.")
        except BadSignature as exc:
            raise ValueError("Invalid state cookie.") from exc
        except Exception as exc:
             raise ValueError("State validation failed.") from exc

        tokens = {}
        if provider == Provider.SPOTIFY:
            tokens = exchange_spotify_code(code)
        elif provider == Provider.TIDAL:
            tokens = exchange_tidal_code(code)

        conn = session.exec(select(Connection).where(Connection.user_id == user.id, Connection.provider == provider)).first()
        if not conn:
            conn = Connection(user_id=user.id, provider=provider, credentials=tokens)
        else:
            conn.credentials = tokens
        session.add(conn)
        session.commit()
        return RedirectResponse("/connect")

    except ValueError as e:
        logger.warning(f"Auth callback warning: {e}")
        return templates.TemplateResponse("connect.html", {
            "request": request,
            "error": str(e),
            **status
        })
    except Exception as e:
        logger.error(f"Auth callback unexpected error: {e}", exc_info=True)
        return templates.TemplateResponse("connect.html", {
            "request": request,
            "error": "An unexpected error occurred during authentication.",
            **status
        })

@router.post("/auth/ytm")
def auth_ytm(
    request: Request,
    headers: str = Form(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:

    valid, msg = ytm.validate_headers(headers)
    if not valid:
        return RedirectResponse("/connect?error=" + msg, status_code=303)

    conn = session.exec(select(Connection).where(Connection.user_id == user.id, Connection.provider == Provider.YTM)).first()
    creds = {"raw": headers}
    if not conn:
        conn = Connection(user_id=user.id, provider=Provider.YTM, credentials=creds)
    else:
        conn.credentials = creds
    session.add(conn)
    session.commit()

    return RedirectResponse("/connect", status_code=303)

@router.post("/auth/qobuz")
def auth_qobuz(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    try:
        creds = login_qobuz(email, password)
    except QobuzError as exc:
        return RedirectResponse(f"/connect?error={exc}", status_code=303)

    conn = session.exec(select(Connection).where(Connection.user_id == user.id, Connection.provider == Provider.QOBUZ)).first()
    if not conn:
        conn = Connection(user_id=user.id, provider=Provider.QOBUZ, credentials=creds)
    else:
        conn.credentials = creds
    session.add(conn)
    session.commit()

    return RedirectResponse("/connect", status_code=303)
