import pytest
from app.config import Settings
from pydantic import ValidationError


def test_development_allows_defaults():
    settings = Settings(
        environment="development",
        secret_key="changeme-secret-key-rotate-in-production",
        auth_password="admin",
    )
    assert settings.environment == "development"


def test_production_rejects_the_default_secret_key():
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            secret_key="changeme-secret-key-rotate-in-production",
            auth_password="a-strong-password",
        )


def test_production_rejects_the_default_password():
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            secret_key="a-strong-secret",
            auth_password="admin",
        )


def test_production_accepts_non_default_credentials():
    settings = Settings(
        environment="production",
        secret_key="a-strong-secret",
        auth_password="a-strong-password",
    )
    assert settings.secret_key == "a-strong-secret"
