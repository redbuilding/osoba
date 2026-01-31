#!/usr/bin/env python3
"""
Migration script: backup conversations and set default model on legacy docs.

What it does
- Creates a JSON backup of the conversations collection (full backup by default).
- Optionally also backs up only targeted (to-be-modified) documents.
- Updates legacy conversations missing a stored model to use a default (e.g., 'gpt-oss:20b').
- Prints a summary of matched/modified counts and lists changed IDs with before/after fields.

Usage
  python scripts/migrate_set_default_model.py \
    --default-model gpt-oss:20b \
    [--backup-only-targeted] [--no-full-backup] [--dry-run]

Environment
  MONGODB_URI (default: mongodb://localhost:27017/)
  MONGODB_DATABASE_NAME (default: mcp_chat_db)
  MONGODB_COLLECTION_NAME (default: conversations)

Notes
- Run with --dry-run first to preview changes.
- Backups are written to ./backups/ with timestamped filenames.
"""

from __future__ import annotations
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from pymongo import MongoClient
from bson import ObjectId


def dumps(obj: Any) -> str:
    return json.dumps(
        obj,
        default=lambda o: str(o) if isinstance(o, (ObjectId, datetime)) else o,
        ensure_ascii=False,
        indent=2,
    )


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_collection(coll, out_dir: Path, filename: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    docs = list(coll.find({}))
    out_path.write_text(dumps(docs), encoding="utf-8")
    return out_path


def backup_targeted(coll, query: Dict[str, Any], out_dir: Path, filename: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    docs = list(coll.find(query))
    out_path.write_text(dumps(docs), encoding="utf-8")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Set default model on legacy conversations")
    parser.add_argument("--default-model", required=True, help="Model tag to set, e.g., gpt-oss:20b")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without updating DB")
    parser.add_argument("--no-full-backup", action="store_true", help="Skip full collection backup")
    parser.add_argument("--backup-only-targeted", action="store_true", help="Also write a backup of just targeted docs")
    args = parser.parse_args()

    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    db_name = os.getenv("MONGODB_DATABASE_NAME", "mcp_chat_db")
    coll_name = os.getenv("MONGODB_COLLECTION_NAME", "conversations")

    client = MongoClient(uri)
    coll = client[db_name][coll_name]

    # Target legacy docs with missing/empty model_name
    query = {
        "$or": [
            {"model_name": {"$exists": False}},
            {"model_name": None},
            {"model_name": ""},
        ]
    }

    total = coll.count_documents({})
    matched = coll.count_documents(query)
    print(f"Database: {db_name}.{coll_name}")
    print(f"Total docs: {total}")
    print(f"Legacy docs (missing model_name): {matched}")

    backups_dir = Path("backups")
    ts = timestamp()

    # Backups
    if not args.no_full_backup:
        full_backup = backup_collection(coll, backups_dir, f"conversations_backup_{ts}.json")
        print(f"Full backup written to: {full_backup}")
    if args.backup_only_targeted:
        targeted_backup = backup_targeted(coll, query, backups_dir, f"conversations_pre_migration_{ts}.json")
        print(f"Targeted backup written to: {targeted_backup}")

    if args.dry_run:
        print("--dry-run: no changes applied.")
        return

    # Collect before/after for reporting
    to_change: List[Dict[str, Any]] = list(coll.find(query, {"_id": 1, "model_name": 1, "ollama_model_name": 1}))
    if not to_change:
        print("No legacy docs found. Nothing to update.")
        return

    default_model = args.default_model
    update = {
        "$set": {
            "model_name": default_model,
            "ollama_model_name": default_model,
        }
    }

    res = coll.update_many(query, update)
    print(f"Matched: {res.matched_count}, Modified: {res.modified_count}")

    changed_ids = {doc["_id"]: {"before": {"model_name": doc.get("model_name"), "ollama_model_name": doc.get("ollama_model_name")}} for doc in to_change}
    # Fetch after
    for doc in coll.find({"_id": {"$in": list(changed_ids.keys())}}, {"_id": 1, "model_name": 1, "ollama_model_name": 1}):
        entry = changed_ids.get(doc["_id"]) or {}
        entry["after"] = {"model_name": doc.get("model_name"), "ollama_model_name": doc.get("ollama_model_name")}
        changed_ids[doc["_id"]] = entry

    report = [
        {
            "_id": str(_id),
            "before": info.get("before"),
            "after": info.get("after"),
        }
        for _id, info in changed_ids.items()
    ]
    out_report = backups_dir / f"conversations_migration_report_{ts}.json"
    out_report.write_text(dumps(report), encoding="utf-8")
    print(f"Report written to: {out_report}")
    print("Changed documents (id: model_name -> model_name):")
    for r in report:
        b = r.get("before") or {}
        a = r.get("after") or {}
        print(f" - {r['_id']}: {b.get('model_name')} -> {a.get('model_name')}")


if __name__ == "__main__":
    main()

