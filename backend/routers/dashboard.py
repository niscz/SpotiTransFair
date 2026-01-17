from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from database import get_session
from models import User, ImportJob, JobStatus, ItemStatus, Provider, ImportItem
from tenant import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
def dashboard(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):

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

    job_by_id = {job.id: job for job in jobs if job.id is not None}

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
    status_days = {
        "done": [],
        "failed": [],
        "waiting": [],
        "running": [],
        "queued": [],
    }
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_labels.append(day.strftime("%a"))
        day_jobs = [job for job in jobs if job.created_at.date() == day]
        day_values.append(len(day_jobs))
        status_days["done"].append(sum(1 for job in day_jobs if normalize_status(job.status) == JobStatus.DONE))
        status_days["failed"].append(sum(1 for job in day_jobs if normalize_status(job.status) == JobStatus.FAILED))
        status_days["waiting"].append(sum(1 for job in day_jobs if normalize_status(job.status) == JobStatus.WAITING_REVIEW))
        status_days["running"].append(
            sum(1 for job in day_jobs if normalize_status(job.status) in {JobStatus.RUNNING, JobStatus.IMPORTING})
        )
        status_days["queued"].append(sum(1 for job in day_jobs if normalize_status(job.status) == JobStatus.QUEUED))

    # Provider mix
    provider_counts = {p: 0 for p in Provider}
    for job in jobs:
        provider_counts[normalize_provider(job.target_provider)] += 1

    provider_series = [provider_counts[Provider.SPOTIFY], provider_counts[Provider.TIDAL], provider_counts[Provider.YTM]]
    provider_labels = ["Spotify", "Tidal", "YouTube Music"]

    # Item status mix
    item_counts = {s: 0 for s in ItemStatus}
    items_by_job = defaultdict(lambda: {"total": 0, "matched": 0, "uncertain": 0, "not_found": 0, "skipped": 0})
    for item in items:
        item_counts[item.status] += 1
        if item.job_id in job_by_id:
            items_by_job[item.job_id]["total"] += 1
            if item.status == ItemStatus.MATCHED:
                items_by_job[item.job_id]["matched"] += 1
            elif item.status == ItemStatus.UNCERTAIN:
                items_by_job[item.job_id]["uncertain"] += 1
            elif item.status == ItemStatus.NOT_FOUND:
                items_by_job[item.job_id]["not_found"] += 1
            elif item.status == ItemStatus.SKIPPED:
                items_by_job[item.job_id]["skipped"] += 1
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

    provider_metrics = {
        provider: {
            "total_jobs": 0,
            "done": 0,
            "failed": 0,
            "waiting": 0,
            "running": 0,
            "matched_items": 0,
            "total_items": 0,
        }
        for provider in Provider
    }
    for job in jobs:
        provider = normalize_provider(job.target_provider)
        metrics = provider_metrics[provider]
        metrics["total_jobs"] += 1
        normalized_status = normalize_status(job.status)
        if normalized_status == JobStatus.DONE:
            metrics["done"] += 1
        elif normalized_status == JobStatus.FAILED:
            metrics["failed"] += 1
        elif normalized_status == JobStatus.WAITING_REVIEW:
            metrics["waiting"] += 1
        elif normalized_status in {JobStatus.RUNNING, JobStatus.IMPORTING}:
            metrics["running"] += 1

    for item in items:
        job = job_by_id.get(item.job_id)
        if not job:
            continue
        provider = normalize_provider(job.target_provider)
        metrics = provider_metrics[provider]
        metrics["total_items"] += 1
        if item.status == ItemStatus.MATCHED:
            metrics["matched_items"] += 1

    provider_table = []
    provider_names = {
        Provider.SPOTIFY: "Spotify",
        Provider.TIDAL: "Tidal",
        Provider.YTM: "YouTube Music",
    }
    for provider, metrics in provider_metrics.items():
        total_items_provider = metrics["total_items"]
        match_rate = round((metrics["matched_items"] / total_items_provider) * 100, 1) if total_items_provider else 0
        provider_table.append({
            "name": provider_names.get(provider, provider.value.title()),
            "provider": provider.value,
            "total_jobs": metrics["total_jobs"],
            "done": metrics["done"],
            "failed": metrics["failed"],
            "waiting": metrics["waiting"],
            "running": metrics["running"],
            "match_rate": match_rate,
            "matched_items": metrics["matched_items"],
            "total_items": total_items_provider,
        })

    job_activity = []
    for job in jobs:
        if job.id is None:
            continue
        counts = items_by_job.get(job.id, {"total": 0, "matched": 0})
        total_item_count = counts["total"]
        matched_count = counts["matched"]
        match_rate = round((matched_count / total_item_count) * 100, 1) if total_item_count else 0
        job_activity.append({
            "id": job.id,
            "source": job.source_playlist_name or job.source_playlist_id,
            "provider": normalize_provider(job.target_provider).value,
            "status": normalize_status(job.status).value,
            "total_items": total_item_count,
            "matched_items": matched_count,
            "match_rate": match_rate,
            "created_at": job.created_at,
        })
    job_activity = sorted(job_activity, key=lambda entry: entry["total_items"], reverse=True)[:6]

    status_timeline_series = [
        {"name": "Done", "data": status_days["done"]},
        {"name": "Failed", "data": status_days["failed"]},
        {"name": "Waiting review", "data": status_days["waiting"]},
        {"name": "Running", "data": status_days["running"]},
        {"name": "Queued", "data": status_days["queued"]},
    ]

    overall_match_rate = round((matched_items / total_items) * 100, 1) if total_items else 0

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
        "status_timeline_series": status_timeline_series,
        "provider_table": provider_table,
        "job_activity": job_activity,
        "overall_match_rate": overall_match_rate,
    })
