from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from core.config import (
    MONGODB_URI,
    MONGODB_DATABASE_NAME,
    MONGODB_COLLECTION_NAME,
    MONGODB_TASKS_COLLECTION_NAME,
    get_logger,
)

logger = get_logger("mongodb_client")

mongo_client = None
db = None
conversations_collection = None
tasks_collection = None
scheduled_tasks_collection = None
templates_collection = None
settings_collection = None

def create_search_indexes():
    """Create text indexes for conversation search."""
    if conversations_collection is None:
        return
    try:
        conversations_collection.create_index([
            ("messages.content", "text"),
            ("title", "text")
        ])
        logger.info("Created search indexes for conversations")
    except Exception as e:
        logger.error(f"Error creating search indexes: {e}")

try:
    mongo_client = MongoClient(MONGODB_URI)
    mongo_client.admin.command('ping')
    db = mongo_client[MONGODB_DATABASE_NAME]
    conversations_collection = db[MONGODB_COLLECTION_NAME]
    tasks_collection = db[MONGODB_TASKS_COLLECTION_NAME]
    scheduled_tasks_collection = db["scheduled_tasks"]
    templates_collection = db["task_templates"]
    settings_collection = db["user_settings"]
    create_search_indexes()
    logger.info(f"Successfully connected to MongoDB: {MONGODB_URI}")
except ConnectionFailure:
    logger.error(f"Failed to connect to MongoDB at {MONGODB_URI}.")
except Exception as e:
    logger.error(f"An error occurred during MongoDB setup: {e}")

def get_conversations_collection():
    if conversations_collection is None:
        raise RuntimeError("MongoDB is not available.")
    return conversations_collection

def get_tasks_collection():
    if tasks_collection is None:
        raise RuntimeError("MongoDB is not available.")
    return tasks_collection

def get_scheduled_tasks_collection():
    if scheduled_tasks_collection is None:
        raise RuntimeError("MongoDB is not available.")
    return scheduled_tasks_collection

def get_templates_collection():
    if templates_collection is None:
        raise RuntimeError("MongoDB is not available.")
    return templates_collection

def get_settings_collection():
    if settings_collection is None:
        raise RuntimeError("MongoDB is not available.")
    return settings_collection
