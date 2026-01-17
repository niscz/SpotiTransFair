from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse, Response, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import get_session
from models import User, ImportJob, ImportItem, ItemStatus, JobStatus, Connection, Provider
from worker import finalize_import_job
from rq import Queue
import redis
import os
import json
from tenant import get_current_user
import ytm
from tidal import TidalClient
from ytm import _headers_to_raw

router = APIRouter()
templates = Jinja2Templates(directory="templates")

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_conn = redis.from_url(redis_url)
q = Queue(connection=redis_conn)

@router.get("/imports/{id}")
def import_detail(
    id: int,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    job = session.get(ImportJob, id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404)

    total = len(job.items)
    matched = len([i for i in job.items if i.status == ItemStatus.MATCHED])
    uncertain = len([i for i in job.items if i.status == ItemStatus.UNCERTAIN])

    failed_items = [i for i in job.items if i.status == ItemStatus.NOT_FOUND]
    skipped_items = [i for i in job.items if i.status == ItemStatus.SKIPPED]

    failed = len(failed_items)
    skipped = len(skipped_items)

    status_series = [matched, uncertain, failed, skipped]
    status_labels = ["Matched", "Uncertain", "Not found", "Skipped"]

    artist_counts = {}
    for item in job.items:
        artists = item.original_track_data.get("artists", []) if item.original_track_data else []
        for artist in artists:
            artist_name = artist.strip()
            if artist_name:
                artist_counts[artist_name] = artist_counts.get(artist_name, 0) + 1

    top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:6]
    top_artist_labels = [name for name, _ in top_artists]
    top_artist_values = [count for _, count in top_artists]

    score_bins = {
        "0-49%": 0,
        "50-74%": 0,
        "75-89%": 0,
        "90-100%": 0,
    }
    for item in job.items:
        if not item.match_data:
            continue
        score = item.match_data.get("_score")
        if score is None:
            continue
        score_percent = max(0, min(100, round(score * 100)))
        if score_percent < 50:
            score_bins["0-49%"] += 1
        elif score_percent < 75:
            score_bins["50-74%"] += 1
        elif score_percent < 90:
            score_bins["75-89%"] += 1
        else:
            score_bins["90-100%"] += 1

    return templates.TemplateResponse("import_detail.html", {
        "request": request,
        "job": job,
        "stats": {
            "total": total,
            "matched": matched,
            "uncertain": uncertain,
            "failed": failed,
            "skipped": skipped,
        },
        "status_series": status_series,
        "status_labels": status_labels,
        "top_artist_labels": top_artist_labels,
        "top_artist_values": top_artist_values,
        "score_labels": list(score_bins.keys()),
        "score_values": list(score_bins.values()),
        "failed_items": failed_items,
        "skipped_items": skipped_items,
    })

@router.get("/imports/{id}/review")
def review_page(
    id: int,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    job = session.get(ImportJob, id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404)
    items = [i for i in job.items if i.status in (ItemStatus.UNCERTAIN, ItemStatus.NOT_FOUND)]

    status_counts = {
        "uncertain": len([i for i in items if i.status == ItemStatus.UNCERTAIN]),
        "not_found": len([i for i in items if i.status == ItemStatus.NOT_FOUND]),
    }
    score_bins = {
        "0-49%": 0,
        "50-74%": 0,
        "75-89%": 0,
        "90-100%": 0,
    }
    score_values = []
    for item in items:
        match_data = item.match_data or {}
        score = match_data.get("_score")
        if score is None:
            continue
        score_percent = max(0, min(100, round(score * 100)))
        score_values.append(score_percent)
        if score_percent < 50:
            score_bins["0-49%"] += 1
        elif score_percent < 75:
            score_bins["50-74%"] += 1
        elif score_percent < 90:
            score_bins["75-89%"] += 1
        else:
            score_bins["90-100%"] += 1

    avg_score = round(sum(score_values) / len(score_values), 1) if score_values else 0

    artist_counts = {}
    for item in items:
        artists = item.original_track_data.get("artists", []) if item.original_track_data else []
        for artist in artists:
            artist_name = artist.strip()
            if artist_name:
                artist_counts[artist_name] = artist_counts.get(artist_name, 0) + 1
    top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return templates.TemplateResponse("review.html", {
        "request": request,
        "job": job,
        "items": items,
        "status_counts": status_counts,
        "avg_score": avg_score,
        "score_labels": list(score_bins.keys()),
        "score_values": list(score_bins.values()),
        "top_artists": top_artists,
    })

@router.post("/imports/{id}/search_track")
def search_track(
    id: int,
    query: str = Form(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> Response:
    if not query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    job = session.get(ImportJob, id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404)

    results = []

    if job.target_provider == Provider.TIDAL:
        conn = session.exec(select(Connection).where(Connection.user_id == user.id, Connection.provider == Provider.TIDAL)).first()
        if not conn:
             raise HTTPException(status_code=400, detail="Not connected to TIDAL")
        client = TidalClient(access_token=conn.credentials.get("access_token"))
        # Tidal returns: id, title, artists (list), album (string), duration (seconds)
        results = client.search_tracks(query, limit=10)

    elif job.target_provider == Provider.YTM:
        conn = session.exec(select(Connection).where(Connection.user_id == user.id, Connection.provider == Provider.YTM)).first()
        if not conn:
             raise HTTPException(status_code=400, detail="Not connected to YouTube Music")

        creds = conn.credentials
        try:
            if isinstance(creds, dict) and "raw" in creds:
                headers_raw = creds["raw"]
            else:
                headers_raw = _headers_to_raw(creds)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid YouTube Music authentication headers") from exc
        if not headers_raw:
            raise HTTPException(status_code=400, detail="YouTube Music authentication headers missing")

        raw_results = ytm.search_tracks(query, headers_raw, filt="songs", top_k=10)

        for r in raw_results:
             artists = [a["name"] for a in r.get("artists", [])]
             results.append({
                 "id": r.get("videoId"),
                 "title": r.get("title"),
                 "artists": artists,
                 "duration": r.get("duration"), # Keep as is (string)
                 "album": r.get("album", {}).get("name") if r.get("album") else None
             })

    return JSONResponse({"results": results})

@router.post("/imports/{id}/review")
def submit_review(
    id: int,
    decisions: str = Form(...), # JSON string
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> Response:
    job = session.get(ImportJob, id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404)
    try:
        decision_list = json.loads(decisions)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid review payload") from exc
    if not isinstance(decision_list, list):
        raise HTTPException(status_code=400, detail="Review payload must be a list")

    for d in decision_list:
        item = session.get(ImportItem, d["item_id"])
        if item and item.job_id == id:
            if d["decision"] == "confirm":
                if d.get("match_id"):
                    item.status = ItemStatus.MATCHED
                    item.selected_match_id = d["match_id"]
                    if d.get("match_data"):
                        item.match_data = d["match_data"]
                elif item.match_data and item.match_data.get("id"):
                    item.status = ItemStatus.MATCHED
                    item.selected_match_id = item.match_data.get("id")
            elif d["decision"] == "reject":
                item.status = ItemStatus.NOT_FOUND
                item.selected_match_id = None
            session.add(item)

    session.commit()
    return RedirectResponse(f"/imports/{id}", status_code=303)

@router.post("/imports/{id}/finalize")
def finalize(
    id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    job = session.get(ImportJob, id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404)
    job.status = JobStatus.IMPORTING
    session.add(job)
    session.commit()

    q.enqueue(finalize_import_job, job.id)
    return RedirectResponse(f"/imports/{id}", status_code=303)
