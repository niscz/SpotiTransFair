import json
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import get_session
from models import User, ImportJob, JobStatus, ItemStatus

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
def dashboard(request: Request, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == "admin")).first()
    if not user:
        # Should not happen given startup
        return "Initializing..."

    jobs = session.exec(select(ImportJob).where(ImportJob.user_id == user.id).order_by(ImportJob.created_at.desc())).all()

    # Chart Data
    # Simple count by date for last 7 days (mock logic for demo)
    # Actually let's just show status distribution
    statuses = {s: 0 for s in JobStatus}
    for j in jobs:
        statuses[j.status] += 1

    chart_series = [statuses[JobStatus.DONE], statuses[JobStatus.FAILED], statuses[JobStatus.QUEUED]]
    chart_labels = ["Done", "Failed", "Queued"]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "jobs": jobs,
        "chart_series": json.dumps(chart_series),
        "chart_labels": json.dumps(chart_labels)
    })
