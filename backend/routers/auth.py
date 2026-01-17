from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import get_session
from models import User, Connection, Provider
from auth import get_spotify_auth_url, get_tidal_auth_url, exchange_spotify_code, exchange_tidal_code
import ytm

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/connect")
def connect_page(request: Request, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == "admin")).first()
    conns = session.exec(select(Connection).where(Connection.user_id == user.id)).all()
    conn_map = {c.provider: True for c in conns}

    return templates.TemplateResponse("connect.html", {
        "request": request,
        "spotify_connected": conn_map.get(Provider.SPOTIFY, False),
        "tidal_connected": conn_map.get(Provider.TIDAL, False),
        "ytm_connected": conn_map.get(Provider.YTM, False)
    })

@router.get("/auth/{provider}/login")
def login(provider: Provider):
    state = "state_123"
    url = "/"
    if provider == Provider.SPOTIFY:
        url = get_spotify_auth_url(state)
    elif provider == Provider.TIDAL:
        url = get_tidal_auth_url(state)
    return RedirectResponse(url)

@router.get("/callback/{provider}")
def callback(provider: Provider, code: str, request: Request, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == "admin")).first()

    try:
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

    except Exception as e:
        return templates.TemplateResponse("connect.html", {
            "request": request,
            "error": str(e),
            "spotify_connected": False, # Simplified, implies reload
            "tidal_connected": False,
            "ytm_connected": False
        })

@router.post("/auth/ytm")
def auth_ytm(request: Request, headers: str = Form(...), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == "admin")).first()

    valid, msg = ytm.validate_headers(headers)
    if not valid:
         # In a real app we'd flash message, here simple return
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
