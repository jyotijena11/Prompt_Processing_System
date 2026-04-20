from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Prompt Processing System"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/prompt_system"
    redis_url: str = "redis://redis:6379/0"

    provider_rate_limit_per_minute: int = 300
    semantic_cache_threshold: float = 0.92
    semantic_cache_top_k: int = 200
    processing_stale_after_seconds: int = 180

    llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    log_level: str = "INFO"
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
