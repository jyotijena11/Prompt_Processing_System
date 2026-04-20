from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import JobStatus


class PromptSubmitRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Prompt text to process")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata")


class PromptSubmitResponse(BaseModel):
    job_id: UUID
    status: str
    message: str


class JobResponse(BaseModel):
    id: UUID
    prompt: str
    status: JobStatus
    metadata: dict[str, Any] | None
    response_text: str | None
    error_message: str | None
    provider_name: str | None
    retry_count: int
    cache_hit: bool
    similarity_score: float | None
    progress: int
    current_stage: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    @classmethod
    def from_model(cls, job):
        return cls(
            id=job.id,
            prompt=job.prompt,
            status=job.status,
            metadata=job.metadata_json,
            response_text=job.response_text,
            error_message=job.error_message,
            provider_name=job.provider_name,
            retry_count=job.retry_count,
            cache_hit=job.cache_hit,
            similarity_score=job.similarity_score,
            progress=job.progress,
            current_stage=job.current_stage,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )


class RateLimitStatus(BaseModel):
    window_key: str
    limit_per_minute: int
    used_in_current_window: int
    remaining_in_current_window: int
    usage_percent: float
    seconds_until_reset: int


class DashboardMetricsResponse(BaseModel):
    total_jobs: int
    queued_jobs: int
    processing_jobs: int
    completed_jobs: int
    failed_jobs: int
    cache_hits: int
    cache_hit_rate_percent: float
    average_similarity_score: float | None
    rate_limit: RateLimitStatus
