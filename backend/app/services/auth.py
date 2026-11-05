from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings


def verify_credentials(username: str, password: str) -> bool:
    return username == settings.auth_username and password == settings.auth_password


def create_access_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"role": "admin", "exp": expire, "type": "access"},
        settings.secret_key,
        algorithm="HS256",
    )


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        return None
