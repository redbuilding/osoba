import logging
import os
from datetime import datetime

# --- Directory Setup ---
# Assumes this file is in backend/core, so we go up two levels to get the project root
# and then into backend/. This makes paths more reliable.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Logging Setup ---
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, 'logs', f"mcp_backend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")),
        logging.StreamHandler()
    ]
)
# Create a logger for the application
def get_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger

# --- Constants ---
WEB_SEARCH_SERVICE_NAME = "web_search_service"
MYSQL_DB_SERVICE_NAME = "mysql_db_service"
HUBSPOT_SERVICE_NAME = "hubspot_service"
YOUTUBE_SERVICE_NAME = "youtube_service"
PYTHON_SERVICE_NAME = "python_service"
CODEX_SERVICE_NAME = "codex_workspace_service"
MAX_DB_RESULT_CHARS = 5000 # Proxy for token limit (approx 1000-1200 tokens)
MAX_TABLES_FOR_SCHEMA_CONTEXT = 7 # Max tables to fetch full schema for, to keep prompt size reasonable

# --- Environment-based Configuration ---
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DATABASE_NAME = os.getenv('MONGODB_DATABASE_NAME', 'mcp_chat_db')
MONGODB_COLLECTION_NAME = os.getenv('MONGODB_COLLECTION_NAME', 'conversations')
# Support both old and new environment variable names for backward compatibility
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL') or os.getenv('DEFAULT_OLLAMA_MODEL', 'devstral:24b')
DEFAULT_REPEAT_PENALTY = float(os.getenv("REPEAT_PENALTY") or os.getenv("OLLAMA_REPEAT_PENALTY", "1.15"))
OLLAMA_API_BASE = os.getenv('OLLAMA_API_BASE', 'http://localhost:11434')

# Tasks feature configuration
MONGODB_TASKS_COLLECTION_NAME = os.getenv('MONGODB_TASKS_COLLECTION_NAME', 'tasks')
ENABLE_TASKS = os.getenv('ENABLE_TASKS', 'true').lower() == 'true'
TASK_MAX_SECONDS_DEFAULT = int(os.getenv('TASK_MAX_SECONDS_DEFAULT', '3600'))
TASK_MAX_TOOL_CALLS_DEFAULT = int(os.getenv('TASK_MAX_TOOL_CALLS_DEFAULT', '50'))
TASK_STEP_TIMEOUT_DEFAULT = int(os.getenv('TASK_STEP_TIMEOUT_DEFAULT', '120'))
TASK_DISPATCH_INTERVAL_MS = int(os.getenv('TASK_DISPATCH_INTERVAL_MS', '2000'))

# Debug / logging flags
CODEX_DEBUG = os.getenv('CODEX_DEBUG', 'false').lower() == 'true'
