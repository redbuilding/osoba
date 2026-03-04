"""Build knowledge base context from indexed documents."""
from typing import Optional
from services.embedder import embed_text
from db.document_store import get_document_store
from core.config import get_logger

logger = get_logger("kb_context")

MAX_KB_CONTEXT_CHARS = 2000
KB_SCORE_THRESHOLD = 0.4


async def build_kb_context(query: str, user_id: str = "default") -> str:
    """Search document knowledge base and return formatted context.

    Args:
        query: User query to search against
        user_id: User ID (reserved for future per-user filtering)

    Returns:
        Formatted context string, or empty string if no relevant docs found
    """
    try:
        if not query or len(query.strip()) < 3:
            return ""

        query_embedding = await embed_text(query)
        store = get_document_store()
        results = store.search_similar(
            query_embedding=query_embedding,
            limit=5,
            score_threshold=KB_SCORE_THRESHOLD
        )

        if not results:
            logger.debug("No relevant document chunks found for KB context")
            return ""

        context_parts = ["Relevant documents:"]
        total_chars = len(context_parts[0])

        for result in results:
            score = result.get("score", 0.0)
            text = result.get("text", "")
            metadata = result.get("metadata", {})
            title = metadata.get("title", "Untitled")

            entry = f"\n- [{title}] (relevance: {score:.0%}): {text[:200]}..."

            if total_chars + len(entry) > MAX_KB_CONTEXT_CHARS:
                break

            context_parts.append(entry)
            total_chars += len(entry)

        if len(context_parts) == 1:
            return ""

        context = "\n".join(context_parts)
        logger.info(f"Built KB context with {len(context_parts)-1} chunks ({total_chars} chars)")
        return context

    except Exception as e:
        logger.error(f"Error building KB context: {e}", exc_info=True)
        return ""
