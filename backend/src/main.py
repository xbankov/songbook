from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
app.mount("/data", StaticFiles(directory="/data"))
templates = Jinja2Templates(directory="static")
path = Path("../../data/after_manual_correction")


@app.get("/api/parse/{filename}")
async def parse(request: Request, filename):
    with open(path / filename, "r", encoding="utf-8") as f:
        content = f.read()
    song = Song.parse(content)
    return templates.TemplateResponse("song.html", {"request": request, "song": song})


@app.get("/")
async def read_root(request: Request):
    songs = [file.name for file in path.iterdir()]
    return templates.TemplateResponse(
        "index.html", {"request": request, "songs": songs}
    )


# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
