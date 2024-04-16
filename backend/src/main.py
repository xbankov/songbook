from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from model.song import Song

app = FastAPI(
    title="Songbook API",
    summary="Retrieve chords for the song from the database or try to download.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/parse/{filename}")
async def parse(filename):
    print(__file__)
    path = Path("../../data/after_manual_correction")
    print(path / filename)
    
    with open(path / filename, "r", encoding="utf-8") as f:
        content = f.read()
    song = Song.parse(content)
    return song.to_json()



@app.get("/")
def read_root():
    return {"Hello": "World"}


# Mount the static files directory
app.mount("/data", StaticFiles(directory="/data"))
