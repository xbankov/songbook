import os


class Settings:
    """
    Represents the settings for the application.

    Attributes:
        MONGODB_URI (str | None): The URI for the MongoDB database.
        Defaults to the value of the environment variable 'MONGODB_URI'.
    """

    MONGODB_URI: str | None = os.getenv("MONGODB_URI")


settings = Settings()
