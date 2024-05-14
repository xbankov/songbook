from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from model.song import Song

app = FastAPI(
    title="Songbook API",
    summary="Explore internet and create your personal guitar chords songbook to print",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

path = Path(__file__).parent.parent.parent / "app/data/" 
app.mount("/app/data", StaticFiles(directory=str(path)))
app.mount("/static", StaticFiles(directory="static"))
templates = Jinja2Templates(directory="static")





@app.get("/")
async def read_root(request: Request):
    songs = [file.name for file in path.iterdir()]
    return templates.TemplateResponse(
        "index.html", {"request": request, "songs": songs}
    )

@app.get("/song/{filename}")
async def parse(request: Request, filename):
    with open(path / filename, "r", encoding="utf-8") as f:
        content = f.read()
    song = Song.parse(content)

    return templates.TemplateResponse("song.html", {"request": request, "song": song})

@app.get("/songbook")
async def parse(request: Request, filename):
    with open(path / filename, "r", encoding="utf-8") as f:
        content = f.read()
    song = Song.parse(content)

    return templates.TemplateResponse("song.html", {"request": request, "song": song})
