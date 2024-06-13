import logging
import os
import traceback
from contextlib import asynccontextmanager

import pymongo
from bson import ObjectId
from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from model.song import Song
from motor.motor_asyncio import AsyncIOMotorClient
from utils import download

logger = logging.getLogger(__file__)


MONGO_HOST = os.getenv("MONGODB_HOST", "mongodb")
MONGO_PORT = os.getenv("MONGODB_PORT", 27017)
MONGO_DB = os.getenv("MONGODB_DATABASE", "songbook")
MONGO_SONGS_COLLECTION = os.getenv("MONGODB_SONGS_COLLECTION", "songs")
MONGO_USERS_COLLECTION = os.getenv("MONGODB_USERS_COLLECTION", "users")
MONGO_SONGBOOKS_COLLECTION = os.getenv("MONGODB_SONGBOOKS_COLLECTION", "songbooks")

MONGO_URL = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}"
print(MONGO_URL)

client = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # Don't remove app argument. Neccessary!

    global client
    client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=2000)
    try:
        info = await client.server_info()
        logger.info("Connected to MongoDB successfully.")
        logger.debug(info)
    except Exception as e:
        logger.error(f"Couldn't connect to the MongoDB{MONGO_URL} due to {e}")
        exit(1)

    db = client.get_database(MONGO_DB)
    collection = db.get_collection(MONGO_SONGS_COLLECTION)
    index_model = [
        ("title", 1),  # Ascending order for 'title'
        ("artist", 1),  # Ascending order for 'artist'
    ]

    try:
        existing_indexes = await collection.index_information()
        if any(
            existing_index["key"] == index_model
            for existing_index in existing_indexes.values()
        ):
            logger.info("Unique index (artist,title) already exists.")
        else:
            await collection.create_index(index_model, unique=True, background=True)
            logger.info("Unique index (artist,title) created successfully.")
    except Exception as e:
        error("Error creating unique index (artist,title)", e)
    yield
    client.close()


def error(message: str, exception: Exception = None, request=None):
    logger.error(f"{message}")
    if exception:
        logger.error(f"Exception: {exception}")
        logger.error(
            f"Traceback: {traceback.format_exc()}",
        )
    if request:
        return templates.TemplateResponse(
            name="error.html",
            request=request,
            context={"error_message": message},
        )


app = FastAPI(
    title="Songbook API",
    summary="Search, add, edit and create your personal guitar chords songbook.",
    lifespan=lifespan,
    static_url_path="/static",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# path = Path(__file__).parent.parent.parent / "app/data/"
# app.mount("/app/data", StaticFiles(directory=str(path)))

app.mount("/static", StaticFiles(directory="static"))
templates = Jinja2Templates(directory="static")


async def get_db():
    db = client.get_database(MONGO_DB)
    return db


@app.get("/")
async def index(request: Request, db=Depends(get_db)):
    collection = db.get_collection(MONGO_SONGS_COLLECTION)

    # Introduce pagination + search + Alphabet filter
    documents = await collection.find().to_list(100)
    songs = [Song.from_json(document) for document in documents]

    return templates.TemplateResponse(
        name="index.html", request=request, context={"songs": songs}
    )


@app.get("/songbook/")
async def get_songbook(request: Request, db=Depends(get_db)):
    collection = db.get_collection(MONGO_SONGS_COLLECTION)
    documents = await collection.find().to_list(100)
    songs = [Song.from_json(document) for document in documents]
    return templates.TemplateResponse(
        "songbook.html", {"request": request, "songs": songs}
    )


@app.get("/add_song")
async def add_song(request: Request, db=Depends(get_db)):
    return templates.TemplateResponse(
        name="add_song.html",
        request=request,
    )


@app.post("/insert")
async def insert_song(request: Request, db=Depends(get_db)):
    form_data = await request.form()
    input_method = form_data["input-method"]

    if input_method == "text-field":
        song = Song.from_chordpro(form_data["chordpro"])
    elif input_method == "url-field":
        url = form_data["url-field"]
        song = download(url)
        if not song:
            return error(
                f"Song couldn't be extracted from url {url}.",
                request=request,
            )
    else:
        return error(f"Input method {input_method} not yet supported", request=request)

    collection = db.get_collection(MONGO_SONGS_COLLECTION)
    song_json = song.json()
    title = song_json["title"]
    artist = song_json["artist"]
    song_index = f"{artist} - {title}"

    try:
        result = await collection.insert_one(song_json)
        logger.info(
            f"Song [{song_index}] with ID: {result.inserted_id} inserted successfully."
        )
    except pymongo.errors.DuplicateKeyError as e:
        error_message = f"Song [{song_index}] already exists and cannot inserted again."
        return error(error_message, e, request=request)

    logger.info(f"Song with ID: {result.inserted_id} inserted successfully.")
    return Response(status_code=status.HTTP_302_FOUND, headers={"Location": "/"})


@app.get("/song/{object_id}")
async def get_song(request: Request, object_id, db=Depends(get_db)):
    collection = db.get_collection(MONGO_SONGS_COLLECTION)
    document = await collection.find_one({"_id": ObjectId(object_id)})
    if document:
        song = Song.from_json(document)
        logger.info(f"Found document: \n{song}")
        return templates.TemplateResponse(
            name="song.html",
            request=request,
            context={"song": song},
        )
    else:
        error_message = f"No documents found with object_id '{object_id}'."
        return error(error_message, request=request)


@app.get("/edit/{object_id}")
async def edit_song(request: Request, object_id: str, db=Depends(get_db)):
    collection = db.get_collection(MONGO_SONGS_COLLECTION)
    document = await collection.find_one({"_id": ObjectId(object_id)})
    if document:
        song = Song.from_json(document)
        return templates.TemplateResponse(
            name="edit_song.html",
            request=request,
            context={"song": song},
        )
    else:
        error_message = f"No documents found with object_id '{object_id}'."
        return error(error_message, request=request)


@app.post("/update/{object_id}")
async def update_song(request: Request, object_id: str, db=Depends(get_db)):
    form_data = await request.form()
    try:
        song = Song.from_chordpro(form_data["chordpro"])
        song.object_id = object_id
    except Exception as e:
        error_message = f"Failed to parse song {form_data['chordpro']}. Conform to Chordpro standards"
        return error(error_message, e, request=request)

    collection = db.get_collection(MONGO_SONGS_COLLECTION)
    result = await collection.update_one(
        {"_id": ObjectId(object_id)}, {"$set": song.json()}
    )

    if result.modified_count == 1:
        logger.info(f"Song with ID: {object_id} updated successfully.")
        return Response(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": f"/song/{object_id}"},
        )
    else:
        error_message = f"Failed to update song: {song.json_meta()}."
        return error(error_message, request=request)


@app.post("/delete/{object_id}")
async def delete_song(request: Request, object_id: str, db=Depends(get_db)):
    collection = db.get_collection(MONGO_SONGS_COLLECTION)
    result = await collection.delete_one({"_id": ObjectId(object_id)})

    if result.deleted_count == 1:
        logger.info(f"Song with ID: {object_id} deleted successfully.")
        return Response(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/"},
        )
    else:
        error_message = f"Failed to delete song with ID: {object_id}."
        return error(error_message, request=request)


@app.get("/artist/{artist_name}")
async def get_artist(request: Request, artist_name: str, db=Depends(get_db)):
    collection = db.get_collection(MONGO_SONGS_COLLECTION)

    documents = await collection.find({"artist": artist_name}).to_list(100)

    if documents:
        songs = [Song.from_json(document) for document in documents]
        logger.info(f"Found {len(songs)} songs by artist: {artist_name}")
        return templates.TemplateResponse(
            "artist.html", {"request": request, "songs": songs, "artist": artist_name}
        )
    else:
        error_message = f"No songs found for artist '{artist_name}'."
        return error(error_message, request=request)
