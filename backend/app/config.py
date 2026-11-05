from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://songbook:changeme@localhost:5432/songbook"
    secret_key: str = "changeme-secret-key-rotate-in-production"
    cors_origins: str = "http://localhost:8081,http://localhost:5173"
    redis_url: str = "redis://localhost:6379/0"
    access_token_expire_minutes: int = 1440
    auth_username: str = "admin"
    auth_password: str = "admin"
    backup_dir: str = "/backups"
    backup_retention_days: int = 7
    database_url_sync: str = "postgresql://songbook:changeme@localhost:5432/songbook"
    upload_dir: str = "/uploads"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
