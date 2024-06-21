from motor.motor_asyncio import AsyncIOMotorClient
from settings import settings
from utils import get_logger

logger = get_logger(__file__)


def get_db_client():
    if settings.MONGODB_URI is None:
        logger.error("No database URI provided. Set the MONGODB_URI variable.")
        exit(1)
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    return client


def init_db():
    pass
    # index_model = [
    #     ("title", 1),  # Ascending order for 'title'
    #     ("artist", 1),  # Ascending order for 'artist'
    # ]

    # try:
    #     existing_indexes = await collection.index_information()
    #     if any(
    #         existing_index["key"] == index_model
    #         for existing_index in existing_indexes.values()
    #     ):
    #         logger.info("Unique index (artist,title) already exists.")
    #     else:
    #         await collection.create_index(index_model, unique=True, background=True)
    #         logger.info("Unique index (artist,title) created successfully.")
    # except Exception as e:
    #     error("Error creating unique index (artist,title)", e)
    # yield
    # client.close()
