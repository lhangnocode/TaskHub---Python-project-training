from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    PROJECT_NAME: str = "TaskHub API"
    DEBUG: bool = True
    SECRET_KEY: str = "super-secret-jwt-key-change-this-in-production-taskhub-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    POSTGRES_SERVER: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "taskhub"
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@db:5432/taskhub"
    )

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_CACHE_TTL_SECONDS: int = 300

    # FastAPI-Mail
    MAIL_USERNAME: str = "noreply@taskhub.com"
    MAIL_PASSWORD: str = "secretpassword"
    MAIL_FROM: str = "noreply@taskhub.com"
    MAIL_PORT: int = 1025
    MAIL_SERVER: str = "localhost"
    MAIL_FROM_NAME: str = "TaskHub Notifications"
    MAIL_STARTTLS: bool = False
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = False
    VALIDATE_CERTS: bool = False
    SUPPRESS_SEND: int = 1


settings = Settings()
