import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from database import get_session
from models import User, ImportJob, JobStatus, ItemStatus, Provider, ImportItem

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
def dashboard(request: Request, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == "admin")).first()
    if not user:
        # Should not happen given startup
        return "Initializing..."

    jobs = session.exec(
        select(ImportJob)
        .where(ImportJob.user_id == user.id)
        .order_by(ImportJob.created_at.desc())
    ).all()

    job_ids = [job.id for job in jobs if job.id is not None]
    items = []
    if job_ids:
        items = session.exec(select(ImportItem).where(ImportItem.job_id.in_(job_ids))).all()

    def normalize_status(status_value: JobStatus | str) -> JobStatus:
        if isinstance(status_value, JobStatus):
            return status_value
        try:
            return JobStatus(status_value)
        except ValueError:
            return JobStatus.QUEUED

    def normalize_provider(provider_value: Provider | str) -> Provider:
        if isinstance(provider_value, Provider):
            return provider_value
        try:
            return Provider(provider_value)
        except ValueError:
            return Provider.YTM

    # Status distribution
    statuses = {s: 0 for s in JobStatus}
    for job in jobs:
        statuses[normalize_status(job.status)] += 1

    chart_series = [
        statuses[JobStatus.DONE],
        statuses[JobStatus.FAILED],
        statuses[JobStatus.WAITING_REVIEW],
        statuses[JobStatus.RUNNING] + statuses[JobStatus.IMPORTING],
        statuses[JobStatus.QUEUED],
    ]
    chart_labels = ["Done", "Failed", "Waiting review", "Running", "Queued"]

    # Daily volume (last 7 days)
    today = datetime.utcnow().date()
    day_labels = []
    day_values = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_labels.append(day.strftime("%a"))
        day_values.append(sum(1 for job in jobs if job.created_at.date() == day))

    # Provider mix
    provider_counts = {p: 0 for p in Provider}
    for job in jobs:
        provider_counts[normalize_provider(job.target_provider)] += 1

    provider_series = [provider_counts[Provider.SPOTIFY], provider_counts[Provider.TIDAL], provider_counts[Provider.YTM]]
    provider_labels = ["Spotify", "Tidal", "YouTube Music"]

    # Item status mix
    item_counts = {s: 0 for s in ItemStatus}
    for item in items:
        item_counts[item.status] += 1
    item_series = [
        item_counts[ItemStatus.MATCHED],
        item_counts[ItemStatus.UNCERTAIN],
        item_counts[ItemStatus.NOT_FOUND],
        item_counts[ItemStatus.SKIPPED],
    ]
    item_labels = ["Matched", "Uncertain", "Not found", "Skipped"]

    total_jobs = len(jobs)
    completed_jobs = statuses[JobStatus.DONE]
    failed_jobs = statuses[JobStatus.FAILED]
    waiting_jobs = statuses[JobStatus.WAITING_REVIEW]
    running_jobs = statuses[JobStatus.RUNNING] + statuses[JobStatus.IMPORTING]
    total_items = len(items)
    matched_items = item_counts[ItemStatus.MATCHED]
    success_rate = round((completed_jobs / total_jobs) * 100, 1) if total_jobs else 0

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "jobs": jobs,
        "chart_series": chart_series,
        "chart_labels": chart_labels,
        "day_labels": day_labels,
        "day_values": day_values,
        "provider_series": provider_series,
        "provider_labels": provider_labels,
        "item_series": item_series,
        "item_labels": item_labels,
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "waiting_jobs": waiting_jobs,
        "running_jobs": running_jobs,
        "total_items": total_items,
        "matched_items": matched_items,
        "success_rate": success_rate,
    })
