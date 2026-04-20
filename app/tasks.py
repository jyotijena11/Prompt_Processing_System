import asyncio
import logging

import redis
from celery import shared_task

from app.config import settings
from app.core.database import SessionLocal
from app.services.llm_provider import get_provider
from app.services.prompt_service import PromptService
from app.services.rate_limiter import GlobalRateLimiter
from app.services.recovery import RecoveryService
from app.services.semantic_cache import SemanticCacheService

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=5)
def process_prompt_job(self, job_id: str):
    db = SessionLocal()
    redis_client = redis.from_url(settings.redis_url)

    prompt_service = PromptService()
    cache_service = SemanticCacheService()
    rate_limiter = GlobalRateLimiter(redis_client)
    provider = get_provider()

    try:
        job = prompt_service.get_job(db, job_id)
        if job is None:
            logger.warning("Job %s not found", job_id)
            return

        prompt_service.mark_processing(db, job)
        prompt_service.update_progress(db, job, 40, "Checking semantic cache")

        cache_match, embedding = cache_service.find_match(db, job.prompt)
        if cache_match:
            prompt_service.update_progress(db, job, 85, "Semantic cache hit")
            prompt_service.mark_completed(
                db,
                job,
                response_text=cache_match.response_text,
                provider_name=cache_match.provider_name,
                cache_hit=True,
                similarity_score=cache_match.score,
            )
            logger.info("Job %s served from semantic cache", job_id)
            return

        prompt_service.update_progress(db, job, 55, "Waiting for provider rate limit slot")
        allowed, delay = rate_limiter.acquire_or_delay()
        if not allowed:
            job.retry_count += 1
            job.current_stage = f"Rate limited, retrying in {delay}s"
            job.progress = 60
            db.commit()
            raise self.retry(countdown=delay)

        prompt_service.update_progress(db, job, 75, "Calling LLM provider")
        response_text = asyncio.run(provider.generate(job.prompt))

        prompt_service.update_progress(db, job, 90, "Saving response and cache entry")
        cache_service.store(
            db=db,
            prompt=job.prompt,
            embedding=embedding,
            response_text=response_text,
            provider_name=provider.provider_name,
        )

        prompt_service.mark_completed(
            db,
            job,
            response_text=response_text,
            provider_name=provider.provider_name,
            cache_hit=False,
            similarity_score=None,
        )
        logger.info("Job %s processed successfully", job_id)

    except Exception as exc:
        job = prompt_service.get_job(db, job_id)
        if job is not None and self.request.retries >= self.max_retries:
            prompt_service.mark_failed(db, job, str(exc), retry_count=self.request.retries)
        logger.exception("Job %s failed: %s", job_id, exc)
        raise
    finally:
        db.close()


@shared_task
def recover_stale_jobs():
    db = SessionLocal()
    recovery_service = RecoveryService()
    try:
        recovered_ids = recovery_service.requeue_stale_jobs(db)
        for job_id in recovered_ids:
            process_prompt_job.delay(job_id)
        return {"recovered_count": len(recovered_ids), "job_ids": recovered_ids}
    finally:
        db.close()
