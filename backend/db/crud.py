from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bson import ObjectId
from db.mongodb import get_conversations_collection
from core.models import ChatMessage

def get_all_conversations() -> List[Dict[str, Any]]:
    """
    Fetches all conversations, sorted by update time, without messages or transcripts.
    Returns a list of raw documents from the database.
    """
    collection = get_conversations_collection()
    cursor = collection.find({}, {"messages": 0, "youtube_transcript": 0}).sort("updated_at", -1).limit(50)
    return list(cursor)

def count_messages_in_conversation(conv_id: ObjectId) -> int:
    """Counts the number of messages in a given conversation."""
    collection = get_conversations_collection()
    # This query efficiently checks for the existence of the first message.
    # count_documents is faster than fetching the whole array.
    return collection.count_documents({"_id": conv_id, "messages.0": {"$exists": True}})

def get_conversation_by_id(conv_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single conversation document by its ID."""
    if not ObjectId.is_valid(conv_id):
        return None
    collection = get_conversations_collection()
    return collection.find_one({"_id": ObjectId(conv_id)})

def get_messages_by_conv_id(conv_id: str) -> Optional[List[ChatMessage]]:
    """Fetches just the messages for a given conversation ID."""
    conv = get_conversation_by_id(conv_id)
    if not conv:
        return None
    return [ChatMessage.model_validate(msg) for msg in conv.get("messages", []) if isinstance(msg, dict)]

def delete_conversation_by_id(conv_id: str) -> bool:
    """Deletes a conversation by its ID. Returns True if successful."""
    if not ObjectId.is_valid(conv_id):
        return False
    collection = get_conversations_collection()
    result = collection.delete_one({"_id": ObjectId(conv_id)})
    return result.deleted_count > 0

def rename_conversation_by_id(conv_id: str, new_title: str) -> Optional[Dict[str, Any]]:
    """Renames a conversation and returns the updated document."""
    if not ObjectId.is_valid(conv_id):
        return None
    collection = get_conversations_collection()
    obj_id = ObjectId(conv_id)

    update_result = collection.update_one(
        {"_id": obj_id},
        {"$set": {"title": new_title, "updated_at": datetime.now(timezone.utc)}}
    )
    if update_result.matched_count == 0:
        return None

    return collection.find_one({"_id": obj_id})
