from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import get_session
from models import User, ImportJob, ImportItem, ItemStatus, JobStatus
from worker import finalize_import_job
from rq import Queue
import redis
import os
import json

router = APIRouter()
templates = Jinja2Templates(directory="templates")

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_conn = redis.from_url(redis_url)
q = Queue(connection=redis_conn)

@router.get("/imports/{id}")
def import_detail(id: int, request: Request, session: Session = Depends(get_session)):
    job = session.get(ImportJob, id)
    if not job:
        raise HTTPException(status_code=404)

    total = len(job.items)
    matched = len([i for i in job.items if i.status == ItemStatus.MATCHED])
    uncertain = len([i for i in job.items if i.status == ItemStatus.UNCERTAIN])
    failed = len([i for i in job.items if i.status == ItemStatus.NOT_FOUND])

    return templates.TemplateResponse("import_detail.html", {
        "request": request,
        "job": job,
        "stats": {
            "total": total,
            "matched": matched,
            "uncertain": uncertain,
            "failed": failed
        }
    })

@router.get("/imports/{id}/review")
def review_page(id: int, request: Request, session: Session = Depends(get_session)):
    job = session.get(ImportJob, id)
    if not job:
        raise HTTPException(status_code=404)
    items = [i for i in job.items if i.status == ItemStatus.UNCERTAIN]

    return templates.TemplateResponse("review.html", {
        "request": request,
        "job": job,
        "items": items
    })

@router.post("/imports/{id}/review")
def submit_review(
    id: int,
    decisions: str = Form(...), # JSON string
    session: Session = Depends(get_session)
):
    job = session.get(ImportJob, id)
    if not job:
        raise HTTPException(status_code=404)
    decision_list = json.loads(decisions) # list of {item_id, decision, match_id?}

    for d in decision_list:
        item = session.get(ImportItem, d["item_id"])
        if item and item.job_id == id:
            if d["decision"] == "confirm":
                item.status = ItemStatus.MATCHED
                if d.get("match_id"):
                    item.selected_match_id = d["match_id"]
                elif item.match_data:
                    item.selected_match_id = item.match_data.get("id")
            elif d["decision"] == "reject":
                item.status = ItemStatus.NOT_FOUND
                item.selected_match_id = None
            session.add(item)

    session.commit()
    return RedirectResponse(f"/imports/{id}", status_code=303)

@router.post("/imports/{id}/finalize")
def finalize(id: int, session: Session = Depends(get_session)):
    job = session.get(ImportJob, id)
    if not job:
        raise HTTPException(status_code=404)
    job.status = JobStatus.IMPORTING
    session.add(job)
    session.commit()

    q.enqueue(finalize_import_job, job.id)
    return RedirectResponse(f"/imports/{id}", status_code=303)
