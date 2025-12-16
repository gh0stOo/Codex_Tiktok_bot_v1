import os
from functools import lru_cache
from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "Codex TikTok SaaS"
    environment: str = Field(default="development")
    secret_key: str = Field(default="dev-secret")
    database_url: str = Field(default="postgresql+psycopg2://codex:codex@db:5432/codex")
    redis_url: str = Field(default="redis://redis:6379/0")
    broker_url: str = Field(default="redis://redis:6379/1")
    storage_backend: str = Field(default="local")
    storage_path: str = Field(default="/data/storage")
    storage_s3_bucket: str = Field(default="codex-bucket")
    storage_s3_region: str = Field(default="us-east-1")
    storage_s3_endpoint: str = Field(default="")
    storage_s3_access_key: str = Field(default="")
    storage_s3_secret_key: str = Field(default="")
    storage_s3_prefix: str = Field(default="")
    use_mock_providers: bool = Field(default=False)
    openrouter_api_key: str = Field(default="", description="Optional; mocked when empty")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    tiktok_client_key: str = Field(default="", description="Optional; mocked when empty")
    tiktok_client_secret: str = Field(default="", description="Optional; mocked when empty")
    tiktok_redirect_uri: str = Field(default="http://localhost:8000/tiktok/oauth/callback")
    tiktok_api_base: str = Field(default="https://open-api.tiktok.com")
    ffmpeg_path: str = Field(default="ffmpeg")
    enable_pgvector: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    demo_email: str = Field(default="demo@codex.dev")
    demo_password: str = Field(default="demopass123")
    fernet_secret: str = Field(default="", description="REQUIRED: Fernet encryption key for secrets. Must be set via environment variable.")
    access_token_exp_minutes: int = Field(default=1440)  # 24 Stunden (statt 15 Minuten)
    refresh_token_exp_days: int = Field(default=30)  # 30 Tage (statt 14)

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    data = {}
    for field in Settings.__fields__:
        env_key = field.upper()
        if env_key in os.environ:
            data[field] = os.environ[env_key]
    settings = Settings(**data)
    
    # Validate critical security settings
    if not settings.fernet_secret or settings.fernet_secret == "change-me-fernet-key":
        raise ValueError(
            "FERNET_SECRET must be set via environment variable. "
            "Generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    
    return settings
