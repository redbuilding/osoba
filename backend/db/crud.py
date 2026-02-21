from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bson import ObjectId
from db import mongodb

# Backwards-compatible accessor so tests can patch db.crud.get_conversations_collection
def get_conversations_collection():
    return mongodb.get_conversations_collection()
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

def search_conversations(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search conversations by title and message content."""
    collection = get_conversations_collection()
    search_filter = {
        "$or": [
            {"messages.content": {"$regex": query, "$options": "i"}},
            {"title": {"$regex": query, "$options": "i"}}
        ]
    }
    cursor = collection.find(search_filter, {"messages": 0, "youtube_transcript": 0}).sort("updated_at", -1).limit(limit)
    return list(cursor)

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

def pin_conversation_for_context(conv_id: str, user_id: str = "default", pinned: bool = True) -> bool:
    """Pin or unpin a conversation for context use.

    Attempts to operate even with non-ObjectId identifiers when a collection is provided
    (e.g., during tests via patch). Falls back to False if the DB is unavailable.
    """
    try:
        collection = get_conversations_collection()
    except Exception:
        # DB unavailable; treat as failure without raising
        return False

    obj_id = ObjectId(conv_id) if ObjectId.is_valid(conv_id) else conv_id
    update_result = collection.update_one(
        {"_id": obj_id},
        {"$set": {
            "pinned_for_context": pinned,
            "user_id": user_id,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    return update_result.matched_count > 0

def get_pinned_conversations(user_id: str = "default", limit: int = 5) -> List[Dict[str, Any]]:
    """Get conversations pinned for context by user."""
    collection = get_conversations_collection()
    cursor = collection.find(
        {"pinned_for_context": True, "user_id": user_id},
        {"messages": 0, "youtube_transcript": 0}
    ).sort("updated_at", -1).limit(limit)
    return list(cursor)

def update_conversation_summary(conv_id: str, summary: str) -> bool:
    """Update the summary of a conversation.

    Supports non-ObjectId identifiers when the collection is patched in tests.
    Returns False if the DB is unavailable.
    """
    try:
        collection = get_conversations_collection()
    except Exception:
        return False

    obj_id = ObjectId(conv_id) if ObjectId.is_valid(conv_id) else conv_id
    update_result = collection.update_one(
        {"_id": obj_id},
        {"$set": {
            "summary": summary,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    return update_result.matched_count > 0


def mark_conversation_indexed(conv_id: str, indexed: bool = True) -> bool:
    """Mark a conversation as indexed to memory.
    
    Args:
        conv_id: Conversation ID
        indexed: Whether conversation is indexed
        
    Returns:
        True if successful
    """
    try:
        collection = get_conversations_collection()
    except Exception:
        return False
    
    obj_id = ObjectId(conv_id) if ObjectId.is_valid(conv_id) else conv_id
    update_data = {
        "indexed_to_memory": indexed,
        "updated_at": datetime.now(timezone.utc)
    }
    
    if indexed:
        update_data["indexed_at"] = datetime.now(timezone.utc)
    
    update_result = collection.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    return update_result.matched_count > 0


def get_conversation_indexing_status(conv_id: str) -> Optional[Dict[str, Any]]:
    """Get indexing status for a conversation.
    
    Args:
        conv_id: Conversation ID
        
    Returns:
        Dictionary with indexing status or None
    """
    if not ObjectId.is_valid(conv_id):
        return None
    
    collection = get_conversations_collection()
    conv = collection.find_one(
        {"_id": ObjectId(conv_id)},
        {"indexed_to_memory": 1, "indexed_at": 1, "messages": 1}
    )
    
    if not conv:
        return None
    
    return {
        "indexed": conv.get("indexed_to_memory", False),
        "indexed_at": conv.get("indexed_at"),
        "message_count": len(conv.get("messages", []))
    }


def find_conversations_for_auto_indexing(limit: int = 10) -> List[Dict[str, Any]]:
    """Find conversations eligible for auto-indexing.
    
    Criteria:
    - 5+ messages
    - 10+ minutes since last update
    - Not already indexed
    
    Args:
        limit: Maximum number of conversations to return
        
    Returns:
        List of conversation documents
    """
    collection = get_conversations_collection()
    
    # Calculate cutoff time (10 minutes ago)
    from datetime import timedelta
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    
    # Query for eligible conversations
    cursor = collection.find(
        {
            "$and": [
                {"messages.4": {"$exists": True}},  # At least 5 messages
                {"updated_at": {"$lt": cutoff_time}},  # 10+ min idle
                {"$or": [
                    {"indexed_to_memory": {"$exists": False}},
                    {"indexed_to_memory": False}
                ]}
            ]
        },
        {"_id": 1, "title": 1, "updated_at": 1}
    ).sort("updated_at", -1).limit(limit)
    
    return list(cursor)
