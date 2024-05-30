from contextlib import asynccontextmanager
import os
from pathlib import Path
from bson import ObjectId
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from motor.motor_asyncio import AsyncIOMotorClient
import logging

import pymongo
from model.song import Song

logger = logging.getLogger(__file__)

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "songbook")
MONGO_SONGS_COLLECTION = os.getenv("MONGO_SONGS_COLLECTION", "songs")
MONGO_USERS_COLLECTION = os.getenv("MONGO_SONGS_COLLECTION", "users")

client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = AsyncIOMotorClient(MONGO_URL)
    index_model = [
        ("title", 1),  # Ascending order for 'title'
        ("artist", 1)  # Ascending order for 'artist'
    ]
    db = client.get_database(MONGO_DB)
    collection = db.get_collection(MONGO_SONGS_COLLECTION)
    try:
        
        existing_indexes = await collection.index_information()
        if any(existing_index["key"] == index_model for existing_index in existing_indexes.values()):
            logger.info("Unique index already exists.")
        else:
            # Create the index if it doesn't exist
            await collection.create_index(index_model, unique=True, background=True)
            logger.info("Unique index created successfully.")
    except Exception as e:
        logger.error(f"Error creating unique index: {e}")
    yield
    client.close()


app = FastAPI(
    title="Songbook API",
    summary="Explore internet and create your personal guitar chords songbook to print",
    lifespan=lifespan,
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
async def index(request: Request):
    db = client.get_database(MONGO_DB)
    collection = db.get_collection(MONGO_SONGS_COLLECTION)
    documents = await collection.find().to_list(100)
    songs = [Song.from_json(document) for document in documents]
    return templates.TemplateResponse(
        "index.html", {"request": request, "songs": songs}
    )


@app.get(f"/insert")
async def test_insert(request: Request):
    with open(path / "Faded.txt", "r", encoding="utf-8") as f:
        content = f.read()
    song = Song.from_chordpro(content)
    db = client.get_database(MONGO_DB)
    collection = db.get_collection(MONGO_SONGS_COLLECTION)
    try:
        result = await collection.insert_one(song.to_json())
    except pymongo.errors.DuplicateKeyError:
        logger.error(f"Song: {song} is already present in unique index (artist, title) and cannot be inserted again")
        return templates.TemplateResponse("error.html", {"request": request})
    logger.info(f"Song with ID: {result.inserted_id} inserted successfully.")
    return Response(status_code=status.HTTP_302_FOUND, headers={"Location": "/"})


@app.get("/song/{object_id}")
async def get_song(request: Request, object_id):
    db = client.get_database(MONGO_DB)
    collection = db.get_collection(MONGO_SONGS_COLLECTION)
    document = await collection.find_one({"_id": ObjectId(object_id)})
    if document:
        song = Song.from_json(document)
        logger.info(f"Found document: \n{song}")
        return templates.TemplateResponse(
            "song.html", {"request": request, "song": song}
        )
    else:
        logger.error(f"No documents found with object_id '{object_id}'.")
        return templates.TemplateResponse("error.html", {"request": request})


@app.get("/songbook")
async def get_songbook(request: Request):
    db = client.get_database(MONGO_DB)
    collection = db.get_collection(MONGO_SONGS_COLLECTION)
    documents = await collection.find().to_list(100)
    songs = [Song.from_json(document) for document in documents]
    return templates.TemplateResponse("book.html", {"request": request, "songs": songs})
