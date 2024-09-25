from motor.motor_asyncio import AsyncIOMotorClient
from settings import settings
from utils import get_logger

logger = get_logger(__file__)


def get_db_client():
    if settings.MONGODB_URI is None:
        logger.error("No database URI provided. Set the MONGODB_URI variable.")
        exit(1)
    client = AsyncIOMotorClient(settings.MONGODB_URI, uuidRepresentation="standard")
    return client
