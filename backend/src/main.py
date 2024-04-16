from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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


@app.get("/api/about")
async def greet():
    return {"message": "Hello from FastAPI!"}


@app.get("/")
def read_root():
    return {"Hello": "World"}

# Mount the static files directory
app.mount("/data", StaticFiles(directory="/data"))
