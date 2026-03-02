"""Memory API endpoints for semantic search and conversation indexing."""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from services.conversation_indexing import index_conversation, find_conversations_to_index
from db.crud import get_conversation_indexing_status
from db.vector_memory import VectorMemory, get_vector_memory
from core.config import get_logger

logger = get_logger("memory_api")

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.post("/conversations/{conv_id}/save")
async def save_conversation_to_memory(conv_id: str) -> Dict[str, Any]:
    """Manually save a conversation to memory.
    
    Args:
        conv_id: Conversation ID to save
        
    Returns:
        Status of the save operation
    """
    try:
        success = await index_conversation(conv_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Conversation {conv_id} saved to memory",
                "conv_id": conv_id
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to save conversation {conv_id}"
            )
            
    except Exception as e:
        logger.error(f"Error saving conversation {conv_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conv_id}/status")
async def get_conversation_memory_status(conv_id: str) -> Dict[str, Any]:
    """Get indexing status for a conversation.
    
    Args:
        conv_id: Conversation ID
        
    Returns:
        Indexing status information
    """
    try:
        status = get_conversation_indexing_status(conv_id)
        
        if status is None:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conv_id} not found"
            )
        
        return {
            "conv_id": conv_id,
            **status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for {conv_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-index")
async def trigger_auto_index() -> Dict[str, Any]:
    """Manually trigger auto-indexing check.
    
    Returns:
        Number of conversations indexed
    """
    try:
        conv_ids = await find_conversations_to_index(limit=10)
        
        indexed_count = 0
        for conv_id in conv_ids:
            success = await index_conversation(conv_id)
            if success:
                indexed_count += 1
        
        return {
            "status": "success",
            "found": len(conv_ids),
            "indexed": indexed_count
        }
        
    except Exception as e:
        logger.error(f"Error in auto-index: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_memory_stats() -> Dict[str, Any]:
    """Get memory system statistics.
    
    Returns:
        Memory statistics
    """
    try:
        vm = get_vector_memory()
        stats = vm.get_stats()
        
        return {
            "status": "ok",
            **stats
        }
        
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_memory(q: str = Query(...), limit: int = Query(10)) -> Dict[str, Any]:
    """Search semantic memory.
    
    Args:
        q: Search query
        limit: Maximum results
        
    Returns:
        Search results
    """
    try:
        from services.embedder import embed_text
        
        # Generate query embedding
        query_embedding = await embed_text(q)
        
        # Search vector memory
        vm = get_vector_memory()
        results = vm.search_similar(
            query_embedding=query_embedding,
            limit=limit,
            score_threshold=0.3
        )
        
        return {
            "status": "success",
            "query": q,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error searching memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conv_id}")
async def remove_conversation_from_memory(conv_id: str) -> Dict[str, Any]:
    """Remove a conversation from memory.
    
    Args:
        conv_id: Conversation ID to remove
        
    Returns:
        Status of removal
    """
    try:
        vm = get_vector_memory()
        success = vm.delete_conversation(conv_id)
        
        if success:
            # Also update MongoDB status
            from db.crud import mark_conversation_indexed
            mark_conversation_indexed(conv_id, indexed=False)
            
            return {
                "status": "success",
                "message": f"Conversation {conv_id} removed from memory"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conv_id} not found in memory"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing conversation {conv_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_all_memory() -> Dict[str, Any]:
    """Clear all memory (dangerous operation).
    
    Returns:
        Status of clear operation
    """
    try:
        # This is a destructive operation - in production, add authentication
        vm = get_vector_memory()
        
        # Get all conversation IDs from collection
        stats = vm.get_stats()
        
        # Delete the entire collection and recreate it
        vm.client.delete_collection(name=vm.collection.name)
        vm.collection = vm.client.get_or_create_collection(
            name=vm.collection.name,
            metadata={"description": "Conversation memory for semantic search"}
        )
        
        return {
            "status": "success",
            "message": "All memory cleared",
            "chunks_removed": stats.get("total_chunks", 0)
        }
        
    except Exception as e:
        logger.error(f"Error clearing memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
