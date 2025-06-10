from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, Response

from backend.core.models import ChatPayload, ChatResponse
from backend.services.chat_service import ChatProcessor, get_logger
from backend.db.mongodb import conversations_collection

router = APIRouter()
logger = get_logger("api_chat")

@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: Request, payload: ChatPayload):
    if conversations_collection is None:
        raise HTTPException(status_code=503, detail="MongoDB unavailable.")
    try:
        processor = ChatProcessor(request, payload)
        return await processor.process_non_streaming()
    except ValueError as e: # Handles invalid conv_id or not found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in /api/chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post("/api/chat/stream")
async def stream_chat_endpoint(request: Request, payload: ChatPayload):
    if conversations_collection is None:
        raise HTTPException(status_code=503, detail="MongoDB unavailable.")
    try:
        processor = ChatProcessor(request, payload)
        return StreamingResponse(processor.process_streaming(), media_type="text/event-stream")
    except Exception as e:
        # This will catch synchronous errors during ChatProcessor initialization.
        # Errors within the stream itself (like ValueError for an invalid conv_id)
        # are handled inside the generator or will terminate the connection.
        logger.error(f"Error setting up chat stream: {e}", exc_info=True)
        return Response(status_code=500, content="Internal server error.")
