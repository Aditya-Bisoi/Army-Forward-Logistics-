from dotenv import load_dotenv
load_dotenv()
import os
import logging

logger = logging.getLogger("db")
mongo_url = os.environ.get("MONGO_URL", "mock")
db_name = os.environ.get("DB_NAME", "army_logistics")

client = None
db = None

if mongo_url and mongo_url.lower() not in ("mock", "memory", "none"):
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        db = client[db_name]
    except Exception as e:
        logger.warning("Motor initialization failed: %s. Using mongomock-motor fallback.", e)
        client = None

if client is None:
    from mongomock_motor import AsyncMongoMockClient
    client = AsyncMongoMockClient()
    db = client[db_name]

