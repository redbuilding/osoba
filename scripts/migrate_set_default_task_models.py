#!/usr/bin/env python3
"""
Migration: backup tasks and scheduled_tasks, set default model on legacy docs.

Usage
  python scripts/migrate_set_default_task_models.py \
    --default-model provider/model-or-tag \
    [--dry-run]

Environment
  MONGODB_URI (default: mongodb://localhost:27017/)
  MONGODB_DATABASE_NAME (default: mcp_chat_db)
  MONGODB_TASKS_COLLECTION_NAME (default: tasks)
  SCHEDULED_TASKS_COLLECTION_NAME (default: scheduled_tasks)
"""
from __future__ import annotations
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from pymongo import MongoClient
from bson import ObjectId


def dumps(obj: Any) -> str:
    return json.dumps(
        obj,
        default=lambda o: str(o) if isinstance(o, (ObjectId, datetime)) else o,
        ensure_ascii=False,
        indent=2,
    )


def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(coll, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    docs = list(coll.find({}))
    out.write_text(dumps(docs), encoding="utf-8")


def migrate_collection(coll, default_model: str, id_field: str = "_id") -> Dict[str, Any]:
    query = {"$or": [
        {"model_name": {"$exists": False}},
        {"model_name": None},
        {"model_name": ""},
    ]}
    before = list(coll.find(query, {id_field: 1, "model_name": 1, "ollama_model_name": 1}))
    if not before:
        return {"matched": 0, "modified": 0, "report": []}
    res = coll.update_many(query, {"$set": {"model_name": default_model, "ollama_model_name": default_model}})
    after_docs = list(coll.find({id_field: {"$in": [b[id_field] for b in before]}}, {id_field: 1, "model_name": 1}))
    after_map = {d[id_field]: d.get("model_name") for d in after_docs}
    report = [{
        "_id": str(b[id_field]),
        "before": {"model_name": b.get("model_name"), "ollama_model_name": b.get("ollama_model_name")},
        "after": {"model_name": after_map.get(b[id_field])},
    } for b in before]
    return {"matched": res.matched_count, "modified": res.modified_count, "report": report}


def main():
    ap = argparse.ArgumentParser(description="Backfill default models for tasks and scheduled tasks")
    ap.add_argument("--default-model", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    db_name = os.getenv("MONGODB_DATABASE_NAME", "mcp_chat_db")
    tasks_name = os.getenv("MONGODB_TASKS_COLLECTION_NAME", "tasks")
    sched_name = os.getenv("SCHEDULED_TASKS_COLLECTION_NAME", "scheduled_tasks")

    client = MongoClient(uri)
    db = client[db_name]
    tasks = db[tasks_name]
    sched = db[sched_name]

    backups_dir = Path("backups")
    now = ts()
    backup(tasks, backups_dir / f"{tasks_name}_backup_{now}.json")
    backup(sched, backups_dir / f"{sched_name}_backup_{now}.json")

    if args.dry_run:
        print("--dry-run set; backups written, no changes applied.")
        return

    t_res = migrate_collection(tasks, args.default_model)
    s_res = migrate_collection(sched, args.default_model)
    report_path = backups_dir / f"tasks_schedules_migration_report_{now}.json"
    report = {"tasks": t_res, "scheduled_tasks": s_res}
    report_path.write_text(dumps(report), encoding="utf-8")
    print(f"Tasks: matched={t_res['matched']}, modified={t_res['modified']}")
    print(f"Scheduled: matched={s_res['matched']}, modified={s_res['modified']}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()

