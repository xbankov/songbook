import pymongo
from bson import ObjectId
from dependencies import get_collection_songs, get_templates
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.templating import Jinja2Templates
from models.song import Song
from motor.motor_asyncio import AsyncIOMotorCollection
from utils import download, get_logger

from .common import show_error

router = APIRouter()

logger = get_logger(__file__)


@router.get("/")
@router.get("/songs")
async def get_songs(
    request: Request,
    collection: AsyncIOMotorCollection = Depends(get_collection_songs),
    templates: Jinja2Templates = Depends(get_templates),
):
    documents = await collection.find().to_list(100)
    songs = [Song.model_validate(document) for document in documents]

    return templates.TemplateResponse(
        name="index.html", request=request, context={"songs": songs}
    )


@router.post("/songs")
async def create_song(
    request: Request,
    collection=Depends(get_collection_songs),
    templates: Jinja2Templates = Depends(get_templates),
):
    form_data = await request.form()
    input_method = form_data["input-method"]

    if input_method == "text-field":
        new_song = Song.from_chordpro(form_data["chordpro"])
    elif input_method == "url-field":
        url = form_data["url-field"]
        new_song = download(url)
        if not new_song:
            return show_error(
                f"Song couldn't be extracted from url {url}.",
                request=request,
                templates=templates,
            )
    elif input_method == "file-field":
        pass

    elif input_method == "import-field":
        pass

    else:
        return show_error(
            f"Input method {input_method} not yet supported",
            request=request,
            templates=templates,
        )

    try:
        created_song = await collection.insert_one(
            new_song.model_dump(by_alias=True, exclude=["id"])
        )
        logger.info(
            f"Song [{new_song.artist} - {new_song.title}] with ID: {created_song.inserted_id} inserted successfully."
        )
    except pymongo.errors.DuplicateKeyError as e:
        error_message = f"Song [{created_song.artist} - {created_song.title}] already exists and cannot be inserted again."
        return show_error(error_message, e, request=request)

    logger.info(f"Song with ID: {created_song.inserted_id} inserted successfully.")
    return Response(status_code=status.HTTP_302_FOUND, headers={"Location": "/"})


@router.get("/songs/add")
async def add_song(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
):
    return templates.TemplateResponse(
        name="add_song.html",
        request=request,
    )


@router.get("/songs/{id}")
async def get_song(
    request: Request,
    id: str,
    collection=Depends(get_collection_songs),
    templates: Jinja2Templates = Depends(get_templates),
):
    document = await collection.find_one({"_id": ObjectId(id)})
    if document:
        song = Song.model_validate(document)
        logger.info(f"Found document: \n{song}")
        return templates.TemplateResponse(
            name="song.html",
            request=request,
            context={"song": song},
        )
    else:
        error_message = f"No documents found with song_id '{id}'."
        return show_error(error_message, request=request)


@router.get("/songs/edit/{song_id}")
async def edit_song(
    request: Request,
    song_id: str,
    collection=Depends(get_collection_songs),
    templates: Jinja2Templates = Depends(get_templates),
):
    document = await collection.find_one({"_id": ObjectId(song_id)})
    if document:
        song = Song.model_validate(document)
        return templates.TemplateResponse(
            name="edit_song.html",
            request=request,
            context={"song": song},
        )
    else:
        error_message = f"No documents found with song_id '{song_id}'."
        return show_error(error_message, request=request)


@router.post("/songs/update/{id}")
async def update_song(
    request: Request,
    id: str,
    collection=Depends(get_collection_songs),
    templates: Jinja2Templates = Depends(get_templates),
):
    form_data = await request.form()
    try:
        song = Song.from_chordpro(form_data["chordpro"])

    except Exception as e:
        error_message = f"Failed to parse song {form_data['chordpro']}. Conform to Chordpro standards"
        return show_error(error_message, e, request=request, templates=templates)

    update_result = await collection.find_one_and_update(
        {"_id": ObjectId(id)},
        {"$set": song.model_dump(exclude={"id"})},
    )
    # update_result.id
    if update_result is not None:
        logger.info(f"Song with ID: {id} updated successfully.")
        return Response(
            status_code=status.HTTP_302_FOUND, headers={"Location": f"/songs/{id}"}
        )
    else:
        error_message = f"Failed to update song: {song.json_meta()}."
        return show_error(error_message, request=request, templates=templates)


@router.post("/songs/delete/{id}", response_description="Delete a song")
async def delete_song(
    request: Request,
    id: str,
    collection=Depends(get_collection_songs),
    templates: Jinja2Templates = Depends(get_templates),
):
    delete_result = await collection.delete_one({"_id": ObjectId(id)})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_302_FOUND, headers={"Location": "/"})

    else:
        error_message = f"Failed to delete song with ID: {id}."
        return show_error(error_message, request=request, templates=templates)
