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
profiles_collection = None
user_profiles_collection = None
heartbeat_insights_collection = None
_initialized = False


def _initialize_mongodb():
    """Lazy initialization of MongoDB connection. Called on first collection access."""
    global mongo_client, db, conversations_collection, tasks_collection
    global scheduled_tasks_collection, templates_collection, settings_collection
    global profiles_collection, user_profiles_collection, heartbeat_insights_collection
    global _initialized

    if _initialized:
        return

    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')
        if '@' not in MONGODB_URI:
            logger.warning(
                "MongoDB connection has no authentication. "
                "For sensitive data, enable MongoDB auth and use a URI with credentials."
            )
        db = mongo_client[MONGODB_DATABASE_NAME]
        conversations_collection = db[MONGODB_COLLECTION_NAME]
        tasks_collection = db[MONGODB_TASKS_COLLECTION_NAME]
        scheduled_tasks_collection = db["scheduled_tasks"]
        templates_collection = db["task_templates"]
        settings_collection = db["user_settings"]
        profiles_collection = db["ai_profiles"]
        user_profiles_collection = db["user_profiles"]
        heartbeat_insights_collection = db["heartbeat_insights"]
        _create_search_indexes()
        _initialized = True
        logger.info(f"Successfully connected to MongoDB: {MONGODB_URI}")
    except ConnectionFailure:
        logger.error(f"Failed to connect to MongoDB at {MONGODB_URI}.")
    except Exception as e:
        logger.error(f"An error occurred during MongoDB setup: {e}")


def _create_search_indexes():
    """Create text indexes for conversation search and context queries."""
    if conversations_collection is None:
        return
    try:
        conversations_collection.create_index([
            ("messages.content", "text"),
            ("title", "text")
        ])
        conversations_collection.create_index([
            ("pinned_for_context", 1),
            ("updated_at", -1)
        ])
        conversations_collection.create_index([
            ("user_id", 1),
            ("pinned_for_context", 1)
        ])
        logger.info("Created search indexes for conversations")
    except Exception as e:
        logger.error(f"Error creating search indexes: {e}")


# Eagerly initialize on import to preserve existing behavior for code that
# references module-level variables directly (e.g. `from db.mongodb import conversations_collection`).
# The key improvement is the 5-second timeout preventing indefinite hangs.
_initialize_mongodb()


def get_conversations_collection():
    _initialize_mongodb()
    if conversations_collection is None:
        raise RuntimeError("MongoDB is not available.")
    return conversations_collection

def get_tasks_collection():
    _initialize_mongodb()
    if tasks_collection is None:
        raise RuntimeError("MongoDB is not available.")
    return tasks_collection

def get_scheduled_tasks_collection():
    _initialize_mongodb()
    if scheduled_tasks_collection is None:
        raise RuntimeError("MongoDB is not available.")
    return scheduled_tasks_collection

def get_templates_collection():
    _initialize_mongodb()
    if templates_collection is None:
        raise RuntimeError("MongoDB is not available.")
    return templates_collection

def get_settings_collection():
    _initialize_mongodb()
    if settings_collection is None:
        raise RuntimeError("MongoDB is not available.")
    return settings_collection

def get_profiles_collection():
    _initialize_mongodb()
    if profiles_collection is None:
        raise RuntimeError("MongoDB is not available.")
    return profiles_collection

def get_user_profiles_collection():
    _initialize_mongodb()
    if user_profiles_collection is None:
        raise RuntimeError("MongoDB is not available.")
    return user_profiles_collection

def get_heartbeat_insights_collection():
    """Get the heartbeat insights collection."""
    _initialize_mongodb()
    if heartbeat_insights_collection is None:
        raise RuntimeError("MongoDB is not available.")
    return heartbeat_insights_collection
