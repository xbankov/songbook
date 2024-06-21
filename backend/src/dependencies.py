from database import get_db_client
from fastapi import Depends
from fastapi.templating import Jinja2Templates
from motor.motor_asyncio import AsyncIOMotorClient


async def get_collection_songs(db_client: AsyncIOMotorClient = Depends(get_db_client)):
    db = db_client.get_database("songbook")
    return db.get_collection("songs")


async def get_collection_songbooks(
    db_client: AsyncIOMotorClient = Depends(get_db_client),
):
    db = db_client.get_database("songbook")
    return db.get_collection("songbooks")


async def get_collection_artists(
    db_client: AsyncIOMotorClient = Depends(get_db_client),
):
    db = db_client.get_database("songbook")
    return db.get_collection("artists")


async def get_collection_users(db_client: AsyncIOMotorClient = Depends(get_db_client)):
    db = db_client.get_database("songbook")
    return db.get_collection("users")


def get_templates():
    return Jinja2Templates(directory="static/templates")
