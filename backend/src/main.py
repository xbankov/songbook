from contextlib import asynccontextmanager

from auth import auth_backend, current_active_user, fastapi_users
from beanie import init_beanie
from database import User, get_db_client
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from models.users import UserCreate, UserRead, UserUpdate
from routes import artists, songs


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_beanie(
        database=get_db_client(),
        document_models=[
            User,
        ],
    )
    yield


app = FastAPI(
    title="Songbook API",
    summary="Search, add, edit and create your personal guitar chords songbook.",
    static_url_path="/static",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(songs.router)
app.include_router(artists.router)

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}
