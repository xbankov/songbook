import pymongo
from bson import ObjectId
from dependencies import get_collection_songs, get_templates
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.templating import Jinja2Templates
from models.song import Song
from utils import download, get_logger

router = APIRouter()

logger = get_logger(__file__)


@router.get("/")
async def index(
    request: Request,
    collection=Depends(get_collection_songs),
    templates: Jinja2Templates = Depends(get_templates),
):
    documents = await collection.find().to_list(100)
    songs = [Song.from_json(document) for document in documents]
    return templates.TemplateResponse(
        name="index.html", request=request, context={"songs": songs}
    )


@router.get("/songbook/")
async def get_songbook(
    request: Request,
    collection=Depends(get_collection_songs),
    templates: Jinja2Templates = Depends(get_templates),
):
    documents = await collection.find().to_list(100)
    songs = [Song.from_json(document) for document in documents]
    return templates.TemplateResponse(
        "songbook.html", {"request": request, "songs": songs}
    )


@router.get("/add_song")
async def add_song(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
):
    return templates.TemplateResponse(
        name="add_song.html",
        request=request,
    )


@router.post("/insert")
async def insert_song(
    request: Request,
    collection=Depends(get_collection_songs),
    templates: Jinja2Templates = Depends(get_templates),
):
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
        error_message = (
            f"Song [{song_index}] already exists and cannot be inserted again."
        )
        return error(error_message, e, request=request)

    logger.info(f"Song with ID: {result.inserted_id} inserted successfully.")
    return Response(status_code=status.HTTP_302_FOUND, headers={"Location": "/"})


@router.get("/song/{object_id}")
async def get_song(
    request: Request,
    object_id,
    collection=Depends(get_collection_songs),
    templates: Jinja2Templates = Depends(get_templates),
):
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


@router.get("/edit/{object_id}")
async def edit_song(
    request: Request,
    object_id: str,
    collection=Depends(get_collection_songs),
    templates: Jinja2Templates = Depends(get_templates),
):
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


@router.post("/update/{object_id}")
async def update_song(
    request: Request,
    object_id: str,
    collection=Depends(get_collection_songs),
):
    form_data = await request.form()
    try:
        song = Song.from_chordpro(form_data["chordpro"])
        song.object_id = object_id
    except Exception as e:
        error_message = f"Failed to parse song {form_data['chordpro']}. Conform to Chordpro standards"
        return error(error_message, e, request=request)

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


@router.post("/delete/{object_id}")
async def delete_song(
    request: Request,
    object_id: str,
    collection=Depends(get_collection_songs),
):
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
