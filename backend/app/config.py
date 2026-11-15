from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://songbook:changeme@localhost:5432/songbook"
    secret_key: str = "changeme-secret-key-rotate-in-production"
    cors_origins: str = "http://localhost:8081,http://localhost:5173"
    redis_url: str = "redis://localhost:6379/0"
    access_token_expire_minutes: int = 1440
    auth_username: str = "admin"
    auth_password: str = "admin"
    environment: str = "development"
    backup_dir: str = "/backups"
    backup_retention_days: int = 7
    database_url_sync: str = "postgresql://songbook:changeme@localhost:5432/songbook"
    upload_dir: str = "/uploads"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if self.environment.lower() != "production":
            return self
        insecure_keys = {
            "",
            "changeme",
            "changeme-secret-key",
            "changeme-secret-key-rotate-in-production",
            "dev-secret-key-not-for-production",
        }
        if self.secret_key in insecure_keys:
            raise ValueError(
                "SECRET_KEY must be set to a non-default value in production"
            )
        if self.auth_password in {"", "admin", "changeme", "password"}:
            raise ValueError(
                "AUTH_PASSWORD must be set to a non-default value in production"
            )
        return self


settings = Settings()
