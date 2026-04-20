from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models import JobStatus, PromptJob


class RecoveryService:
    def requeue_stale_jobs(self, db: Session) -> list[str]:
        cutoff = datetime.utcnow() - timedelta(seconds=settings.processing_stale_after_seconds)
        stale_jobs = (
            db.query(PromptJob)
            .filter(PromptJob.status == JobStatus.processing)
            .filter(PromptJob.started_at.is_not(None))
            .filter(PromptJob.started_at < cutoff)
            .all()
        )

        recovered_ids = []
        for job in stale_jobs:
            job.status = JobStatus.queued
            job.error_message = "Recovered after stale processing timeout"
            recovered_ids.append(str(job.id))

        db.commit()
        return recovered_ids
