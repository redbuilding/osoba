"""Build hybrid context combining pinned conversations and semantic memory."""
from typing import Optional
from services.embedder import embed_text
from db.vector_memory import VectorMemory, get_vector_memory
from core.config import get_logger

logger = get_logger("semantic_memory_context")

MAX_MEMORY_CONTEXT_CHARS = 2500
SIMILARITY_THRESHOLD = 0.6


async def build_memory_context(
    query: str,
    user_id: str = "default",
    current_conv_id: Optional[str] = None
) -> str:
    """Build semantic memory context for a query.
    
    Args:
        query: User query to search for relevant memories
        user_id: User ID for filtering
        current_conv_id: Current conversation ID to exclude from results
        
    Returns:
        Formatted context string from relevant past conversations
    """
    try:
        if not query or len(query.strip()) < 3:
            logger.debug("Query too short for memory search")
            return ""
        
        # Generate query embedding
        query_embedding = await embed_text(query)
        
        # Search vector memory
        vm = get_vector_memory()
        results = vm.search_similar(
            query_embedding=query_embedding,
            limit=5,
            score_threshold=SIMILARITY_THRESHOLD
        )
        
        if not results:
            logger.debug("No relevant memories found")
            return ""
        
        # Filter out current conversation
        if current_conv_id:
            results = [r for r in results if r.get("conv_id") != current_conv_id]
        
        if not results:
            return ""
        
        # Format context
        context_parts = ["Relevant past conversations:"]
        total_chars = len(context_parts[0])
        
        for result in results:
            conv_id = result.get("conv_id", "unknown")
            score = result.get("score", 0.0)
            text = result.get("text", "")
            metadata = result.get("metadata", {})
            title = metadata.get("title", "Untitled")
            
            # Format entry
            entry = f"\n- [{title}] (relevance: {score:.0%}): {text[:200]}..."
            
            # Check if adding this entry would exceed limit
            if total_chars + len(entry) > MAX_MEMORY_CONTEXT_CHARS:
                break
            
            context_parts.append(entry)
            total_chars += len(entry)
        
        if len(context_parts) == 1:
            return ""
        
        context = "\n".join(context_parts)
        logger.info(f"Built memory context with {len(context_parts)-1} conversations ({total_chars} chars)")
        return context
        
    except Exception as e:
        logger.error(f"Error building memory context: {e}", exc_info=True)
        return ""
