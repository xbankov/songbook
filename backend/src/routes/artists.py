from dependencies import get_collection_songs, get_templates
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from models.song import Song
from utils import get_logger

router = APIRouter()

logger = get_logger(__file__)


@router.get(
    "/artist/{artist_name}",
)
async def get_artist(
    request: Request,
    artist_name: str,
    collection=Depends(get_collection_songs),
    templates: Jinja2Templates = Depends(get_templates),
):
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
