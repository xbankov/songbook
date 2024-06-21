from dependencies import get_collection_songs, get_templates
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from models.song import Song
from utils import get_logger

router = APIRouter()

logger = get_logger(__file__)


@router.get("/songbook/")
async def get_songbook(
    request: Request,
    collection=Depends(get_collection_songs),
    templates: Jinja2Templates = Depends(get_templates),
):
    documents = await collection.find().to_list(100)
    songs = [Song.model_validate(document) for document in documents]
    return templates.TemplateResponse(
        "songbook.html", {"request": request, "songs": songs}
    )
