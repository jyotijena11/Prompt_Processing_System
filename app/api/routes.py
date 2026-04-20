import redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import get_db
from app.schemas import DashboardMetricsResponse, JobResponse, PromptSubmitRequest, PromptSubmitResponse
from app.services.prompt_service import PromptService
from app.services.rate_limiter import GlobalRateLimiter
from app.tasks import process_prompt_job

router = APIRouter()
prompt_service = PromptService()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/prompts", response_model=PromptSubmitResponse)
def submit_prompt(payload: PromptSubmitRequest, db: Session = Depends(get_db)):
    job = prompt_service.create_job(db, payload.prompt, payload.metadata)
    process_prompt_job.delay(str(job.id))
    return PromptSubmitResponse(
        job_id=job.id,
        status=job.status.value,
        message="Prompt accepted and queued for processing",
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = prompt_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.from_model(job)


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(limit: int = 50, db: Session = Depends(get_db)):
    jobs = prompt_service.list_jobs(db, limit=limit)
    return [JobResponse.from_model(job) for job in jobs]


@router.get("/dashboard/metrics", response_model=DashboardMetricsResponse)
def dashboard_metrics(db: Session = Depends(get_db)):
    redis_client = redis.from_url(settings.redis_url)
    metrics = prompt_service.dashboard_metrics(db)
    rate_limit = GlobalRateLimiter(redis_client).get_usage_snapshot()
    return DashboardMetricsResponse(**metrics, rate_limit=rate_limit)
