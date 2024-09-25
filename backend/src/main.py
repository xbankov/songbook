from posixpath import realpath

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import artists, index, songs

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
app.mount(
    "/static",
    StaticFiles(directory=realpath(f"{realpath(__file__)}/../static")),
    name="static",
)
app.include_router(index.router)
app.include_router(songs.router)
app.include_router(artists.router)
