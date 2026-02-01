import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv, find_dotenv
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Load .env early so all downstream modules see environment variables
_dotenv_path = find_dotenv(usecwd=True, raise_error_if_not_found=False)
if _dotenv_path:
    load_dotenv(_dotenv_path)
else:
    load_dotenv()

from core.config import get_logger, BASE_DIR
from services.mcp_service import start_mcp_services, stop_mcp_services
from services.task_runner import start_task_dispatcher
from services.task_scheduler import scheduler
from services.template_initializer import initialize_default_templates
from db.mongodb import mongo_client
from api import chat, conversations, status, tasks, scheduled_tasks, providers, codex, profiles, artifacts
from auth_hubspot import router as hubspot_auth_router
from services.artifact_service import _artifacts_root_abs

logger = get_logger("mcp_backend_main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    logger.info("FastAPI Lifespan: Starting up...")
    start_mcp_services()
    logger.info("FastAPI Lifespan: MCP services started, starting task dispatcher...")
    try:
        await start_task_dispatcher()
        logger.info("FastAPI Lifespan: Task dispatcher started successfully")
    except Exception as e:
        logger.error(f"FastAPI Lifespan: Failed to start task dispatcher: {e}", exc_info=True)
    
    logger.info("FastAPI Lifespan: Starting scheduler...")
    await scheduler.start()
    logger.info("FastAPI Lifespan: Starting template initializer...")
    await initialize_default_templates()
    logger.info("FastAPI Lifespan: Startup complete")
    yield
    logger.info("FastAPI Lifespan: Shutting down...")
    await scheduler.stop()
    await stop_mcp_services()
    if mongo_client:
        mongo_client.close()
        logger.info("FastAPI Lifespan: MongoDB connection closed.")

# --- FastAPI App Initialization ---
app = FastAPI(lifespan=lifespan)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routers ---
app.include_router(hubspot_auth_router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(status.router)
app.include_router(tasks.router)
app.include_router(scheduled_tasks.router)
app.include_router(providers.router)
app.include_router(profiles.router)
app.include_router(codex.router)
app.include_router(artifacts.router)

# --- Static Files Hosting ---
# Note: Mount more specific prefixes (e.g., /artifacts) BEFORE mounting the root "/" static app
# to avoid the root mount catching prefixed paths first.

# Artifacts mount first so it takes precedence over "/"
try:
    artifacts_dir = str(_artifacts_root_abs())
    if not os.path.exists(artifacts_dir):
        os.makedirs(artifacts_dir, exist_ok=True)
    logger.info(f"Mounting artifacts directory at /artifacts -> {artifacts_dir}")
    app.mount("/artifacts", StaticFiles(directory=artifacts_dir, html=False), name="artifacts_static")
except Exception as e:
    logger.error(f"Failed to mount artifacts directory: {e}")

# Frontend static at root
frontend_dist_path = os.path.join(BASE_DIR, '..', 'frontend', 'dist')
if os.path.exists(frontend_dist_path):
    logger.info(f"Serving static files from: {frontend_dist_path}")
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="static_frontend")
else:
    logger.warning(f"Frontend build directory not found: {frontend_dist_path}. Run 'npm run build' in 'frontend' directory.")

# --- Main Execution ---
if __name__ == "__main__":
    logger.info("Starting Uvicorn for development. MCP services startup handled by FastAPI's lifespan manager.")
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=True,
        reload_dirs=[BASE_DIR] # Reload when any backend file changes
    )
