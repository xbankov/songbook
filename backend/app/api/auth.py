from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import LoginRequest, Token
from app.services.auth import create_access_token, verify_credentials

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(body: LoginRequest):
    if not verify_credentials(body.username, body.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return Token(
        access_token=create_access_token(),
        token_type="bearer",
    )
