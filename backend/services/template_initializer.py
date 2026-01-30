from db.mongodb import get_templates_collection
from data.default_templates import get_default_templates
from core.config import get_logger

logger = get_logger("template_initializer")

async def initialize_default_templates():
    """Initialize default templates if they don't exist."""
    try:
        collection = get_templates_collection()
        
        # Check if templates already exist
        existing_count = collection.count_documents({})
        if existing_count > 0:
            logger.info(f"Templates already exist ({existing_count} found), skipping initialization")
            return
        
        # Insert default templates
        default_templates = get_default_templates()
        if default_templates:
            collection.insert_many(default_templates)
            logger.info(f"Initialized {len(default_templates)} default templates")
        
    except Exception as e:
        logger.error(f"Error initializing default templates: {e}")
