"""Document Knowledge Base API endpoints."""
import base64
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from core.config import get_logger
from db.documents_crud import (
    create_document,
    get_document,
    list_documents,
    delete_document as db_delete_document,
)
from db.document_store import get_document_store
from services.document_parser import parse_file, parse_url
from services.document_indexing import index_document

logger = get_logger("api.documents")

router = APIRouter(prefix="/api/documents", tags=["documents"])

LARGE_DOC_THRESHOLD = 50_000  # chars — above this, index in background


class UploadPayload(BaseModel):
    filename: str
    data_b64: str
    title: str
    description: Optional[str] = ""
    user_id: Optional[str] = "default"


class UrlPayload(BaseModel):
    url: str
    title: str
    description: Optional[str] = ""
    user_id: Optional[str] = "default"


def _serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict."""
    if doc is None:
        return {}
    result = {}
    for k, v in doc.items():
        if k == "_id":
            result["id"] = str(v)
        elif hasattr(v, "isoformat"):
            result[k] = v.isoformat()
        else:
            result[k] = v
    # Don't return full content in list views (can be large)
    return result


@router.post("/upload")
async def upload_document(payload: UploadPayload, background_tasks: BackgroundTasks):
    """Upload a file (base64-encoded) and index it."""
    try:
        content_bytes = base64.b64decode(payload.data_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 data")

    try:
        text, file_type = parse_file(payload.filename, content_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    doc = {
        "user_id": payload.user_id,
        "title": payload.title,
        "description": payload.description or "",
        "source_type": "upload",
        "source_url": "",
        "file_type": file_type,
        "content": text,
        "char_count": len(text),
        "indexed": False,
        "indexed_at": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    doc_id = create_document(doc)
    logger.info(f"Created document {doc_id}: {payload.title} ({len(text)} chars)")

    if len(text) > LARGE_DOC_THRESHOLD:
        background_tasks.add_task(index_document, doc_id)
        indexed_status = "indexing"
    else:
        success = await index_document(doc_id)
        indexed_status = "indexed" if success else "index_failed"

    return {
        "success": True,
        "id": doc_id,
        "title": payload.title,
        "file_type": file_type,
        "char_count": len(text),
        "indexed_status": indexed_status,
    }


@router.post("/url")
async def ingest_url(payload: UrlPayload, background_tasks: BackgroundTasks):
    """Fetch a URL and index its content."""
    try:
        text = parse_url(payload.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    doc = {
        "user_id": payload.user_id,
        "title": payload.title,
        "description": payload.description or "",
        "source_type": "url",
        "source_url": payload.url,
        "file_type": "url",
        "content": text,
        "char_count": len(text),
        "indexed": False,
        "indexed_at": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    doc_id = create_document(doc)
    logger.info(f"Created URL document {doc_id}: {payload.title} ({len(text)} chars)")

    if len(text) > LARGE_DOC_THRESHOLD:
        background_tasks.add_task(index_document, doc_id)
        indexed_status = "indexing"
    else:
        success = await index_document(doc_id)
        indexed_status = "indexed" if success else "index_failed"

    return {
        "success": True,
        "id": doc_id,
        "title": payload.title,
        "file_type": "url",
        "char_count": len(text),
        "indexed_status": indexed_status,
    }


@router.get("")
async def list_docs(user_id: str = "default", limit: int = 100):
    """List all documents for a user."""
    docs = list_documents(user_id=user_id, limit=limit)
    serialized = []
    for doc in docs:
        d = _serialize_doc(doc)
        d.pop("content", None)  # Don't send full content in list
        serialized.append(d)
    return {"documents": serialized, "count": len(serialized)}


@router.get("/search")
async def search_docs(q: str, limit: int = 5):
    """Semantic search over indexed documents."""
    from services.embedder import embed_text
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")

    query_embedding = await embed_text(q)
    store = get_document_store()
    results = store.search_similar(query_embedding, limit=limit, score_threshold=0.3)
    return {"results": results, "count": len(results)}


@router.get("/stats")
async def get_stats(user_id: str = "default"):
    """Get document knowledge base statistics."""
    docs = list_documents(user_id=user_id, limit=1000)
    store = get_document_store()
    vector_stats = store.get_stats()

    indexed_count = sum(1 for d in docs if d.get("indexed"))
    total_chars = sum(d.get("char_count", 0) for d in docs)

    return {
        "document_count": len(docs),
        "indexed_count": indexed_count,
        "total_chars": total_chars,
        "total_chunks": vector_stats.get("total_chunks", 0),
    }


@router.get("/{doc_id}")
async def get_doc(doc_id: str):
    """Get a document by ID (includes content)."""
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _serialize_doc(doc)


@router.delete("/{doc_id}")
async def delete_doc(doc_id: str):
    """Delete a document from MongoDB and ChromaDB."""
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove from vector store
    store = get_document_store()
    store.delete_document(doc_id)

    # Remove from MongoDB
    db_delete_document(doc_id)
    logger.info(f"Deleted document {doc_id}")

    return {"success": True, "id": doc_id}
