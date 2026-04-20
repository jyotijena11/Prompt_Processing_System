from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import JobStatus, PromptJob


class PromptService:
    def create_job(self, db: Session, prompt: str, metadata: dict | None) -> PromptJob:
        job = PromptJob(
            prompt=prompt,
            metadata_json=metadata,
            status=JobStatus.queued,
            progress=5,
            current_stage="Queued for processing",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def get_job(self, db: Session, job_id: UUID | str) -> PromptJob | None:
        return db.query(PromptJob).filter(PromptJob.id == job_id).first()

    def list_jobs(self, db: Session, limit: int = 50) -> list[PromptJob]:
        return db.query(PromptJob).order_by(PromptJob.created_at.desc()).limit(limit).all()

    def update_progress(self, db: Session, job: PromptJob, progress: int, stage: str) -> PromptJob:
        job.progress = progress
        job.current_stage = stage
        job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
        return job

    def mark_processing(self, db: Session, job: PromptJob) -> PromptJob:
        job.status = JobStatus.processing
        job.started_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        job.progress = 25
        job.current_stage = "Worker picked up request"
        db.commit()
        db.refresh(job)
        return job

    def mark_completed(
        self,
        db: Session,
        job: PromptJob,
        response_text: str,
        provider_name: str,
        cache_hit: bool = False,
        similarity_score: float | None = None,
    ) -> PromptJob:
        job.status = JobStatus.completed
        job.response_text = response_text
        job.provider_name = provider_name
        job.cache_hit = cache_hit
        job.similarity_score = similarity_score
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        job.progress = 100
        job.current_stage = "Completed" if not cache_hit else "Completed from semantic cache"
        db.commit()
        db.refresh(job)
        return job

    def mark_failed(self, db: Session, job: PromptJob, error_message: str, retry_count: int | None = None) -> PromptJob:
        job.status = JobStatus.failed
        job.error_message = error_message
        if retry_count is not None:
            job.retry_count = retry_count
        job.updated_at = datetime.utcnow()
        job.progress = 100
        job.current_stage = "Failed"
        db.commit()
        db.refresh(job)
        return job

    def dashboard_metrics(self, db: Session) -> dict:
        total_jobs = db.query(func.count(PromptJob.id)).scalar() or 0
        queued_jobs = db.query(func.count(PromptJob.id)).filter(PromptJob.status == JobStatus.queued).scalar() or 0
        processing_jobs = db.query(func.count(PromptJob.id)).filter(PromptJob.status == JobStatus.processing).scalar() or 0
        completed_jobs = db.query(func.count(PromptJob.id)).filter(PromptJob.status == JobStatus.completed).scalar() or 0
        failed_jobs = db.query(func.count(PromptJob.id)).filter(PromptJob.status == JobStatus.failed).scalar() or 0
        cache_hits = db.query(func.count(PromptJob.id)).filter(PromptJob.cache_hit.is_(True)).scalar() or 0
        average_similarity_score = db.query(func.avg(PromptJob.similarity_score)).filter(PromptJob.similarity_score.is_not(None)).scalar()
        cache_hit_rate_percent = round((cache_hits / completed_jobs) * 100, 2) if completed_jobs else 0.0

        return {
            "total_jobs": total_jobs,
            "queued_jobs": queued_jobs,
            "processing_jobs": processing_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "cache_hits": cache_hits,
            "cache_hit_rate_percent": cache_hit_rate_percent,
            "average_similarity_score": round(float(average_similarity_score), 4) if average_similarity_score is not None else None,
        }
