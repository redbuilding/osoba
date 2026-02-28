"""Embedding service using Ollama nomic-embed-text model."""
import asyncio
import ollama
from typing import List
from core.config import get_logger

logger = get_logger("embedder")

MODEL_NAME = "nomic-embed-text"
EMBEDDING_DIMENSION = 768


async def embed_text(text: str) -> List[float]:
    """Generate embedding for a single text using nomic-embed-text via Ollama.
    
    Args:
        text: Text to embed
        
    Returns:
        List of floats representing the embedding vector (768 dimensions)
    """
    try:
        response = await asyncio.to_thread(ollama.embeddings, model=MODEL_NAME, prompt=text)
        embedding = response.get("embedding", [])
        
        if not embedding:
            logger.warning(f"Empty embedding returned for text: {text[:50]}...")
            return [0.0] * EMBEDDING_DIMENSION
            
        logger.debug(f"Generated embedding with {len(embedding)} dimensions")
        return embedding
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}", exc_info=True)
        return [0.0] * EMBEDDING_DIMENSION


async def embed_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    embeddings = []
    for text in texts:
        embedding = await embed_text(text)
        embeddings.append(embedding)
    
    logger.info(f"Generated {len(embeddings)} embeddings")
    return embeddings
