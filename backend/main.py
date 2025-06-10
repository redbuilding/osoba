import os
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_logger, BASE_DIR
from backend.services.mcp_service import start_mcp_services, stop_mcp_services
from backend.db.mongodb import mongo_client
from backend.api import chat, conversations, status
from backend.auth_hubspot import router as hubspot_auth_router

logger = get_logger("mcp_backend_main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    start_mcp_services()
    yield
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

# --- Static Files Hosting ---
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
