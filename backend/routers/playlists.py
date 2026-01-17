from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import get_session
from models import User, Connection, Provider, ImportJob, JobStatus
from spotify import SpotifyClient
from rq import Queue
import redis
import os
from worker import process_import_job

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Redis Queue (re-init here or share singleton)
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_conn = redis.from_url(redis_url)
q = Queue(connection=redis_conn)

@router.get("/playlists")
def playlists_page(request: Request, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == "admin")).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    conn = session.exec(select(Connection).where(Connection.user_id == user.id, Connection.provider == Provider.SPOTIFY)).first()

    playlists = []
    error = None

    if conn:
        client = SpotifyClient(access_token=conn.credentials.get("access_token"), refresh_token=conn.credentials.get("refresh_token"))
        try:
            data = client.get_user_playlists(limit=50)
            for item in data.get("items", []):
                if item:
                    img = item["images"][0]["url"] if item.get("images") else None
                    playlists.append({
                        "id": item["id"],
                        "name": item["name"],
                        "tracks": item["tracks"]["total"],
                        "image": img,
                        "url": item["external_urls"]["spotify"]
                    })
        except Exception as e:
            error = str(e)
    else:
        error = "Not connected to Spotify"

    return templates.TemplateResponse("playlists.html", {
        "request": request,
        "playlists": playlists,
        "error": error
    })

@router.post("/imports/create")
def create_import(
    request: Request,
    playlist_ids: str = Form(...), # Comma separated
    target_provider: str = Form(...),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.username == "admin")).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check connection
    try:
        target_enum = Provider(target_provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid target provider") from exc
    conn = session.exec(select(Connection).where(Connection.user_id == user.id, Connection.provider == target_enum)).first()
    if not conn:
        # In real app render with error
        return RedirectResponse("/playlists?error=Not+connected+to+target", status_code=303)

    pids = playlist_ids.split(",")
    for pid in pids:
        if not pid.strip(): continue

        job = ImportJob(
            user_id=user.id,
            source_playlist_id=pid.strip(),
            target_provider=target_enum,
            status=JobStatus.QUEUED
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        q.enqueue(process_import_job, job.id)

    return RedirectResponse("/", status_code=303)
