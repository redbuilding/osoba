"""MongoDB CRUD for document knowledge base."""
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from bson import ObjectId

from db.mongodb import get_documents_collection


def _obj_id(doc_id: str) -> ObjectId:
    if not ObjectId.is_valid(doc_id):
        raise ValueError("Invalid document id")
    return ObjectId(doc_id)


def create_document(doc: Dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    doc.setdefault("created_at", now)
    doc.setdefault("updated_at", now)
    doc.setdefault("indexed", False)
    res = get_documents_collection().insert_one(doc)
    return str(res.inserted_id)


def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    return get_documents_collection().find_one({"_id": _obj_id(doc_id)})


def list_documents(user_id: str = "default", limit: int = 100) -> List[Dict[str, Any]]:
    cur = get_documents_collection().find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(limit)
    return list(cur)


def update_document(doc_id: str, patch: Dict[str, Any]) -> None:
    patch = {**patch, "updated_at": datetime.now(timezone.utc)}
    get_documents_collection().update_one({"_id": _obj_id(doc_id)}, {"$set": patch})


def delete_document(doc_id: str) -> bool:
    result = get_documents_collection().delete_one({"_id": _obj_id(doc_id)})
    return result.deleted_count > 0


def mark_document_indexed(doc_id: str) -> None:
    get_documents_collection().update_one(
        {"_id": _obj_id(doc_id)},
        {"$set": {
            "indexed": True,
            "indexed_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }}
    )
