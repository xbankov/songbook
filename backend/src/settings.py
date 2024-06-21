import os


class Settings:
    MONGODB_URI: str | None = os.getenv("MONGODB_URI")


settings = Settings()
