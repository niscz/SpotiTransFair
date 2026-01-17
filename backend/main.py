from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import os
import redis
from rq import Queue

from database import init_db, get_session, engine
from models import User, Connection, ImportJob, ImportItem, Provider, JobStatus, ItemStatus
from auth import get_spotify_auth_url, get_tidal_auth_url, exchange_spotify_code, exchange_tidal_code
from worker import process_import_job, finalize_import_job
from spotify import SpotifyClient
import ytm

app = FastAPI(title="SpotiTransFair")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis Queue
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_conn = redis.from_url(redis_url)
q = Queue(connection=redis_conn)

@app.on_event("startup")
def on_startup():
    init_db()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == "admin")).first()
        if not user:
            user = User(username="admin")
            session.add(user)
            session.commit()

# --- Auth ---

@app.get("/auth/{provider}/login")
def login(provider: Provider):
    state = "state_123"
    if provider == Provider.SPOTIFY:
        return {"url": get_spotify_auth_url(state)}
    elif provider == Provider.TIDAL:
        return {"url": get_tidal_auth_url(state)}
    else:
        raise HTTPException(status_code=400, detail="Invalid provider for OAuth")

class AuthCallback(BaseModel):
    code: str
    state: Optional[str] = None

@app.post("/auth/{provider}/callback")
def callback(provider: Provider, data: AuthCallback, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == "admin")).first()

    if provider == Provider.SPOTIFY:
        tokens = exchange_spotify_code(data.code)
        conn = session.exec(select(Connection).where(Connection.user_id == user.id, Connection.provider == Provider.SPOTIFY)).first()
        if not conn:
            conn = Connection(user_id=user.id, provider=Provider.SPOTIFY, credentials=tokens)
        else:
            conn.credentials = tokens
        session.add(conn)
        session.commit()
        return {"status": "ok"}

    elif provider == Provider.TIDAL:
        tokens = exchange_tidal_code(data.code)
        conn = session.exec(select(Connection).where(Connection.user_id == user.id, Connection.provider == Provider.TIDAL)).first()
        if not conn:
            conn = Connection(user_id=user.id, provider=Provider.TIDAL, credentials=tokens)
        else:
            conn.credentials = tokens
        session.add(conn)
        session.commit()
        return {"status": "ok"}
    else:
        raise HTTPException(status_code=400, detail="Invalid provider")

class YTMAuth(BaseModel):
    headers: str

@app.post("/auth/ytm")
def auth_ytm(data: YTMAuth, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == "admin")).first()

    valid, msg = ytm.validate_headers(data.headers)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    conn = session.exec(select(Connection).where(Connection.user_id == user.id, Connection.provider == Provider.YTM)).first()
    creds = {"raw": data.headers}
    if not conn:
        conn = Connection(user_id=user.id, provider=Provider.YTM, credentials=creds)
    else:
        conn.credentials = creds
    session.add(conn)
    session.commit()
    return {"status": "ok"}

@app.get("/user/connections")
def get_connections(session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == "admin")).first()
    conns = session.exec(select(Connection).where(Connection.user_id == user.id)).all()
    return {c.provider: True for c in conns}

# --- Playlists ---

@app.get("/playlists")
def get_playlists(session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == "admin")).first()
    conn = session.exec(select(Connection).where(Connection.user_id == user.id, Connection.provider == Provider.SPOTIFY)).first()

    if not conn:
        raise HTTPException(status_code=401, detail="Spotify not connected")

    client = SpotifyClient(access_token=conn.credentials.get("access_token"), refresh_token=conn.credentials.get("refresh_token"))

    try:
        data = client.get_user_playlists(limit=50)
        playlists = []
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
        return playlists
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Imports & Review ---

class CreateImportRequest(BaseModel):
    playlist_id: str
    target_provider: Provider

@app.post("/imports")
def create_import(data: CreateImportRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == "admin")).first()

    conn = session.exec(select(Connection).where(Connection.user_id == user.id, Connection.provider == data.target_provider)).first()
    if not conn:
        raise HTTPException(status_code=400, detail=f"Not connected to {data.target_provider}")

    job = ImportJob(
        user_id=user.id,
        source_playlist_id=data.playlist_id,
        target_provider=data.target_provider,
        status=JobStatus.QUEUED
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    q.enqueue(process_import_job, job.id)
    return job

@app.get("/imports")
def list_imports(session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == "admin")).first()
    jobs = session.exec(select(ImportJob).where(ImportJob.user_id == user.id).order_by(ImportJob.created_at.desc())).all()
    return jobs

@app.get("/imports/{id}")
def get_import(id: int, session: Session = Depends(get_session)):
    job = session.get(ImportJob, id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    total = len(job.items)
    matched = len([i for i in job.items if i.status == ItemStatus.MATCHED])
    uncertain = len([i for i in job.items if i.status == ItemStatus.UNCERTAIN])
    failed = len([i for i in job.items if i.status == ItemStatus.NOT_FOUND])

    return {
        "job": job,
        "stats": {
            "total": total,
            "matched": matched,
            "uncertain": uncertain,
            "failed": failed
        }
    }

@app.get("/imports/{id}/review")
def get_import_review(id: int, session: Session = Depends(get_session)):
    job = session.get(ImportJob, id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    items = [i for i in job.items if i.status == ItemStatus.UNCERTAIN]
    return items

class ReviewDecision(BaseModel):
    item_id: int
    decision: str
    match_id: Optional[str] = None

class ReviewRequest(BaseModel):
    decisions: List[ReviewDecision]

@app.post("/imports/{id}/review")
def submit_review(id: int, data: ReviewRequest, session: Session = Depends(get_session)):
    job = session.get(ImportJob, id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    for d in data.decisions:
        item = session.get(ImportItem, d.item_id)
        if item and item.job_id == id:
            if d.decision == "confirm":
                item.status = ItemStatus.MATCHED
                if d.match_id:
                    item.selected_match_id = d.match_id
                elif item.match_data:
                    item.selected_match_id = item.match_data.get("id")
            elif d.decision == "reject":
                item.status = ItemStatus.NOT_FOUND
                item.selected_match_id = None
            session.add(item)

    session.commit()
    return {"status": "ok"}

@app.post("/imports/{id}/finalize")
def finalize_import(id: int, session: Session = Depends(get_session)):
    job = session.get(ImportJob, id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = JobStatus.IMPORTING
    session.add(job)
    session.commit()

    q.enqueue(finalize_import_job, job.id)
    return {"status": "importing"}
