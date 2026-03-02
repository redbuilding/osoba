"""Vector memory storage using ChromaDB for semantic search."""
import chromadb
from chromadb import PersistentClient
import tiktoken
from typing import List, Dict, Any, Optional
from pathlib import Path
from core.config import get_logger

logger = get_logger("vector_memory")

CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 50  # tokens
COLLECTION_NAME = "conversations"
CHROMA_PATH = ".chroma"


class VectorMemory:
    """ChromaDB-based vector storage for conversation memory."""
    
    def __init__(self, persist_directory: str = CHROMA_PATH):
        """Initialize ChromaDB persistent client.
        
        Args:
            persist_directory: Directory for ChromaDB persistent storage
        """
        self.persist_directory = persist_directory
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        try:
            self.client = PersistentClient(path=persist_directory)
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={
                    "description": "Conversation memory for semantic search",
                    "hnsw:space": "cosine"
                }
            )
            logger.info(f"Initialized ChromaDB at {persist_directory}")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}", exc_info=True)
            raise
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            tokens = encoding.encode(text)
            
            chunks = []
            start = 0
            while start < len(tokens):
                end = start + CHUNK_SIZE
                chunk_tokens = tokens[start:end]
                chunk_text = encoding.decode(chunk_tokens)
                chunks.append(chunk_text)
                start += (CHUNK_SIZE - CHUNK_OVERLAP)
            
            logger.debug(f"Split text into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking text: {e}", exc_info=True)
            return [text]  # Return original text as single chunk on error
    
    def add_conversation(
        self,
        conv_id: str,
        chunks: List[str],
        embeddings: List[List[float]],
        metadata: Dict[str, Any]
    ) -> bool:
        """Store conversation chunks with embeddings.
        
        Args:
            conv_id: Conversation ID
            chunks: List of text chunks
            embeddings: List of embedding vectors
            metadata: Metadata for the conversation
            
        Returns:
            True if successful
        """
        try:
            # Generate unique IDs for each chunk
            ids = [f"{conv_id}_chunk_{i}" for i in range(len(chunks))]
            
            # Add metadata to each chunk
            metadatas = [
                {**metadata, "conv_id": conv_id, "chunk_index": i}
                for i in range(len(chunks))
            ]
            
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas
            )
            
            logger.info(f"Added conversation {conv_id} with {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error adding conversation {conv_id}: {e}", exc_info=True)
            return False
    
    def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Search for similar conversations.
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of results with conversation IDs, scores, and metadata
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            # Format results
            formatted_results = []
            if results and results.get("ids") and len(results["ids"]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    # ChromaDB cosine distance: similarity = 1 - distance
                    distance = results["distances"][0][i] if results.get("distances") else 1.0
                    similarity = 1.0 - distance
                    
                    if similarity >= score_threshold:
                        formatted_results.append({
                            "id": doc_id,
                            "conv_id": results["metadatas"][0][i].get("conv_id"),
                            "score": similarity,
                            "text": results["documents"][0][i] if results.get("documents") else "",
                            "metadata": results["metadatas"][0][i] if results.get("metadatas") else {}
                        })
            
            logger.info(f"Found {len(formatted_results)} similar conversations (threshold: {score_threshold})")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching similar conversations: {e}", exc_info=True)
            return []
    
    def delete_conversation(self, conv_id: str) -> bool:
        """Remove conversation from memory.
        
        Args:
            conv_id: Conversation ID to remove
            
        Returns:
            True if successful
        """
        try:
            # Find all chunks for this conversation
            results = self.collection.get(
                where={"conv_id": conv_id}
            )
            
            if results and results.get("ids"):
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted conversation {conv_id} ({len(results['ids'])} chunks)")
                return True
            else:
                logger.warning(f"Conversation {conv_id} not found in memory")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting conversation {conv_id}: {e}", exc_info=True)
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics.
        
        Returns:
            Dictionary with collection stats
        """
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": COLLECTION_NAME,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            return {"total_chunks": 0, "error": str(e)}


# Singleton instance
_vector_memory: Optional[VectorMemory] = None


def get_vector_memory(persist_directory: str = CHROMA_PATH) -> VectorMemory:
    """Get or create the VectorMemory singleton.
    
    Args:
        persist_directory: Directory for ChromaDB persistent storage
        
    Returns:
        VectorMemory singleton instance
    """
    global _vector_memory
    if _vector_memory is None:
        _vector_memory = VectorMemory(persist_directory)
    return _vector_memory
