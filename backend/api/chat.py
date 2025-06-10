from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

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
    except ValueError as e: # Handles invalid conv_id or not found
        # Cannot return HTTPException for a stream, so we log and close.
        # The frontend will need to handle a prematurely closed connection.
        logger.error(f"Error starting stream: {e}")
        return Response(status_code=404, content=str(e))
    except Exception as e:
        logger.error(f"Error in /api/chat/stream endpoint: {e}", exc_info=True)
        return Response(status_code=500, content="Internal server error.")
