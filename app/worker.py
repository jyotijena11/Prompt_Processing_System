from celery import Celery

from app.config import settings


celery_app = Celery(
    "prompt_processing_system",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    timezone="UTC",
    beat_schedule={
        "recover-stale-jobs-every-minute": {
            "task": "app.tasks.recover_stale_jobs",
            "schedule": 60.0,
        }
    },
)
