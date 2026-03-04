"""Vector store for document knowledge base using ChromaDB."""
import chromadb
from chromadb import PersistentClient
import tiktoken
from typing import List, Dict, Any, Optional
from pathlib import Path
from core.config import get_logger

logger = get_logger("document_store")

CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 50  # tokens
COLLECTION_NAME = "documents"
CHROMA_PATH = ".chroma"


class DocumentVectorStore:
    """ChromaDB-based vector storage for document knowledge base."""

    def __init__(self, persist_directory: str = CHROMA_PATH):
        self.persist_directory = persist_directory
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        try:
            self.client = PersistentClient(path=persist_directory)
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={
                    "description": "Document knowledge base for semantic search",
                    "hnsw:space": "cosine"
                }
            )
            logger.info(f"Initialized document store ChromaDB at {persist_directory}")
        except Exception as e:
            logger.error(f"Error initializing document store ChromaDB: {e}", exc_info=True)
            raise

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
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
            return [text]

    def add_document(
        self,
        doc_id: str,
        chunks: List[str],
        embeddings: List[List[float]],
        metadata: Dict[str, Any]
    ) -> bool:
        """Store document chunks with embeddings."""
        try:
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    **metadata,
                    "doc_id": doc_id,
                    "chunk_index": i
                }
                for i in range(len(chunks))
            ]
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas
            )
            logger.info(f"Added document {doc_id} with {len(chunks)} chunks")
            return True
        except Exception as e:
            logger.error(f"Error adding document {doc_id}: {e}", exc_info=True)
            return False

    def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: float = 0.4
    ) -> List[Dict[str, Any]]:
        """Search for similar document chunks."""
        try:
            count = self.collection.count()
            if count == 0:
                return []

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(limit, count)
            )

            formatted_results = []
            if results and results.get("ids") and len(results["ids"]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i] if results.get("distances") else 1.0
                    similarity = 1.0 - distance

                    if similarity >= score_threshold:
                        formatted_results.append({
                            "id": doc_id,
                            "doc_id": results["metadatas"][0][i].get("doc_id"),
                            "score": similarity,
                            "text": results["documents"][0][i] if results.get("documents") else "",
                            "metadata": results["metadatas"][0][i] if results.get("metadatas") else {}
                        })

            logger.info(f"Found {len(formatted_results)} similar document chunks (threshold: {score_threshold})")
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching document store: {e}", exc_info=True)
            return []

    def delete_document(self, doc_id: str) -> bool:
        """Remove all chunks for a document."""
        try:
            results = self.collection.get(where={"doc_id": doc_id})
            if results and results.get("ids"):
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted document {doc_id} ({len(results['ids'])} chunks)")
                return True
            else:
                logger.warning(f"Document {doc_id} not found in store")
                return False
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}", exc_info=True)
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": COLLECTION_NAME,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error(f"Error getting document store stats: {e}", exc_info=True)
            return {"total_chunks": 0, "error": str(e)}


# Singleton instance
_document_store: Optional[DocumentVectorStore] = None


def get_document_store(persist_directory: str = CHROMA_PATH) -> DocumentVectorStore:
    """Get or create the DocumentVectorStore singleton."""
    global _document_store
    if _document_store is None:
        _document_store = DocumentVectorStore(persist_directory)
    return _document_store
