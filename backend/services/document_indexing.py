"""Index documents into ChromaDB for semantic search."""
from core.config import get_logger
from db.documents_crud import get_document, mark_document_indexed
from db.document_store import get_document_store
from services.embedder import embed_batch

logger = get_logger("document_indexing")


async def index_document(doc_id: str) -> bool:
    """Chunk, embed, and store a document in the vector store.

    Args:
        doc_id: MongoDB document ID

    Returns:
        True if indexing succeeded
    """
    try:
        doc = get_document(doc_id)
        if not doc:
            logger.error(f"Document {doc_id} not found in MongoDB")
            return False

        content = doc.get("content", "")
        if not content:
            logger.error(f"Document {doc_id} has no content to index")
            return False

        store = get_document_store()
        chunks = store.chunk_text(content)

        if not chunks:
            logger.error(f"No chunks generated for document {doc_id}")
            return False

        logger.info(f"Indexing document {doc_id}: {len(chunks)} chunks")
        embeddings = await embed_batch(chunks)

        metadata = {
            "title": doc.get("title", "Untitled"),
            "source_type": doc.get("source_type", "upload"),
            "file_type": doc.get("file_type", "txt"),
            "user_id": doc.get("user_id", "default"),
            "created_at": str(doc.get("created_at", "")),
        }

        success = store.add_document(doc_id, chunks, embeddings, metadata)
        if success:
            mark_document_indexed(doc_id)
            logger.info(f"Successfully indexed document {doc_id}")
        return success

    except Exception as e:
        logger.error(f"Error indexing document {doc_id}: {e}", exc_info=True)
        return False
