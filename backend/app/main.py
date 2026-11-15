from contextlib import asynccontextmanager

from app.api import artists, auth, backup, export, search_import
from app.api import settings as settings_router
from app.api import songbooks, songs
from app.config import settings
from app.database import init_db
from app.dependencies import require_auth
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Songbook API",
    description="Personal guitar chords songbook with versioning, import, and PDF export.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public endpoints: /api/health, /api/auth/login, and the generated API docs
# (/api/docs, /api/openapi.json). Every other router below requires a token.
app.include_router(auth.router)
app.include_router(songs.router, dependencies=[Depends(require_auth)])
app.include_router(songbooks.router, dependencies=[Depends(require_auth)])
app.include_router(artists.router, dependencies=[Depends(require_auth)])
app.include_router(export.router, dependencies=[Depends(require_auth)])
app.include_router(search_import.router, dependencies=[Depends(require_auth)])
app.include_router(backup.router, dependencies=[Depends(require_auth)])
app.include_router(settings_router.router, dependencies=[Depends(require_auth)])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
