from typing import List
from fastapi import APIRouter, HTTPException, Response, status

from backend.core.models import ConversationListItem, ChatMessage, RenamePayload
from backend.db import crud
from backend.services.ollama_service import get_default_ollama_model
from backend.core.config import get_logger

router = APIRouter()
logger = get_logger("api_conversations")

@router.get("/api/conversations", response_model=List[ConversationListItem], response_model_by_alias=False)
async def list_conversations():
    try:
        db_convs = crud.get_all_conversations()
        conv_list_items = []
        default_model_cache = None

        for doc in db_convs:
            doc["message_count"] = crud.count_messages_in_conversation(doc["_id"])
            if not doc.get("ollama_model_name"):
                if default_model_cache is None:
                    default_model_cache = await get_default_ollama_model()
                doc["ollama_model_name"] = default_model_cache
            conv_list_items.append(ConversationListItem.model_validate(doc))
        return conv_list_items
    except Exception as e:
        logger.error(f"Error listing conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error listing conversations.")

@router.get("/api/conversations/{conversation_id}", response_model=List[ChatMessage])
async def get_conversation_messages(conversation_id: str):
    try:
        messages = crud.get_messages_by_conv_id(conversation_id)
        if messages is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        return messages
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages for conversation {conversation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching conversation details.")

@router.delete("/api/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_endpoint(conversation_id: str):
    try:
        success = crud.delete_conversation_by_id(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found for deletion.")
        logger.info(f"Deleted conversation ID: {conversation_id}")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting conversation.")

@router.put("/api/conversations/{conversation_id}/rename", response_model=ConversationListItem, response_model_by_alias=False)
async def rename_conversation_title_endpoint(conversation_id: str, payload: RenamePayload):
    try:
        updated_doc = crud.rename_conversation_by_id(conversation_id, payload.new_title)
        if not updated_doc:
            raise HTTPException(status_code=404, detail="Conversation not found for renaming.")

        updated_doc["message_count"] = crud.count_messages_in_conversation(updated_doc["_id"])
        if not updated_doc.get("ollama_model_name"):
            updated_doc["ollama_model_name"] = await get_default_ollama_model()

        logger.info(f"Renamed conversation ID {conversation_id} to '{payload.new_title}'")
        return ConversationListItem.model_validate(updated_doc)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming conversation {conversation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error renaming conversation.")
