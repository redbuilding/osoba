"""Service to index conversations to vector memory for semantic search."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from services.embedder import embed_batch
from db.vector_memory import VectorMemory, get_vector_memory
from db.crud import get_conversation_by_id, get_conversations_collection
from core.config import get_logger

logger = get_logger("conversation_indexing")

MIN_MESSAGES_FOR_INDEXING = 5
IDLE_MINUTES_FOR_INDEXING = 10


async def index_conversation(conv_id: str) -> bool:
    """Index a single conversation to vector memory.
    
    Args:
        conv_id: Conversation ID to index
        
    Returns:
        True if successfully indexed
    """
    try:
        # Get conversation
        conversation = get_conversation_by_id(conv_id)
        if not conversation:
            logger.warning(f"Conversation {conv_id} not found")
            return False
        
        # Check message count
        messages = conversation.get("messages", [])
        if len(messages) < MIN_MESSAGES_FOR_INDEXING:
            logger.info(f"Conversation {conv_id} has only {len(messages)} messages, skipping")
            return False
        
        # Extract conversation text
        text_parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if content:
                text_parts.append(f"{role}: {content}")
        
        full_text = "\n\n".join(text_parts)
        
        # Initialize vector memory
        vm = get_vector_memory()
        
        # Chunk the conversation
        chunks = vm.chunk_text(full_text)
        
        # Generate embeddings
        embeddings = await embed_batch(chunks)
        
        # Prepare metadata
        metadata = {
            "title": conversation.get("title", "Untitled"),
            "message_count": len(messages),
            "created_at": conversation.get("created_at", datetime.now(timezone.utc)).isoformat(),
            "updated_at": conversation.get("updated_at", datetime.now(timezone.utc)).isoformat()
        }
        
        # Add to vector memory
        success = vm.add_conversation(
            conv_id=conv_id,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata
        )
        
        if success:
            # Mark as indexed in MongoDB
            from db.crud import mark_conversation_indexed
            mark_conversation_indexed(conv_id, indexed=True)
            logger.info(f"Successfully indexed conversation {conv_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error indexing conversation {conv_id}: {e}", exc_info=True)
        return False


async def find_conversations_to_index(limit: int = 10) -> List[str]:
    """Find conversations that need indexing.
    
    Args:
        limit: Maximum number of conversations to return
        
    Returns:
        List of conversation IDs
    """
    try:
        from db.crud import find_conversations_for_auto_indexing
        conversations = find_conversations_for_auto_indexing(limit=limit)
        conv_ids = [str(conv["_id"]) for conv in conversations]
        logger.info(f"Found {len(conv_ids)} conversations to index")
        return conv_ids
        
    except Exception as e:
        logger.error(f"Error finding conversations to index: {e}", exc_info=True)
        return []
