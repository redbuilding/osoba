import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional
import croniter
from core.config import get_logger
from services.schedule_utils import compute_next_run
from db.mongodb import get_scheduled_tasks_collection
from db.tasks_crud import create_task
from core.models import TaskCreatePayload

logger = get_logger("task_scheduler")

class TaskScheduler:
    def __init__(self):
        self.scheduled_tasks: Dict[str, dict] = {}
        self.running = False
        self._task = None

    async def start(self):
        """Start the scheduler."""
        if self.running:
            return
        
        self.running = True
        await self.load_scheduled_tasks()
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Task scheduler started")

    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Task scheduler stopped")

    async def load_scheduled_tasks(self):
        """Load scheduled tasks from database."""
        try:
            collection = get_scheduled_tasks_collection()
            tasks = list(collection.find({"schedule.enabled": True}))
            
            for task_doc in tasks:
                task_id = str(task_doc["_id"])
                # Ensure in-memory copy retains _id for later updates
                self.scheduled_tasks[task_id] = task_doc

                # Calculate next run time with timezone awareness
                next_run, err = compute_next_run(task_doc.get("schedule", {}), now_utc=datetime.now(timezone.utc))
                if next_run:
                    # Update next_run in database
                    collection.update_one(
                        {"_id": task_doc["_id"]},
                        {"$set": {"schedule.next_run": next_run}}
                    )
                    # Update memory
                    task_doc.setdefault("schedule", {})["next_run"] = next_run
                else:
                    logger.warning(f"Scheduled task {task_id} has no computable next_run: {err}")
                
            logger.info(f"Loaded {len(self.scheduled_tasks)} scheduled tasks")
        except Exception as e:
            logger.error(f"Error loading scheduled tasks: {e}")

    async def schedule_task(self, task_doc: dict) -> str:
        """Add a new scheduled task."""
        try:
            collection = get_scheduled_tasks_collection()
            # Calculate next run time (UTC)
            next_run, err = compute_next_run(task_doc.get("schedule", {}), now_utc=datetime.now(timezone.utc))
            if not next_run:
                raise RuntimeError(f"Unable to schedule task: {err}")
            task_doc["schedule"]["next_run"] = next_run
            task_doc["created_at"] = datetime.now(timezone.utc)
            task_doc["run_count"] = 0
            
            result = collection.insert_one(task_doc)
            task_id = str(result.inserted_id)
            # Keep ObjectId in in-memory copy for update ops
            task_doc["_id"] = result.inserted_id
            self.scheduled_tasks[task_id] = task_doc
            logger.info(f"Scheduled task {task_id}: {task_doc['name']}")
            
            return task_id
        except Exception as e:
            logger.error(f"Error scheduling task: {e}")
            raise

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                await self._check_and_execute_due_tasks()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)

    async def _check_and_execute_due_tasks(self):
        """Check for and execute due tasks."""
        now = datetime.now(timezone.utc)
        
        for task_id, scheduled_task in list(self.scheduled_tasks.items()):
            try:
                next_run = scheduled_task.get("schedule", {}).get("next_run")
                if not next_run:
                    continue
                
                # Ensure next_run is timezone-aware for comparison
                if hasattr(next_run, 'tzinfo') and next_run.tzinfo is None:
                    next_run = next_run.replace(tzinfo=timezone.utc)
                
                if next_run > now:
                    continue
                
                # Execute the task
                await self._execute_scheduled_task(task_id, scheduled_task)
                
                # Update schedule based on type
                schedule = scheduled_task.get("schedule", {})
                s_type = (schedule.get("type") or "recurring").lower()

                next_run_utc = None
                if s_type == "recurring":
                    next_run_utc, _ = compute_next_run(schedule, now_utc=now)

                # Update database
                collection = get_scheduled_tasks_collection()
                update_patch = {"last_run": now}
                if next_run_utc:
                    update_patch["schedule.next_run"] = next_run_utc
                if s_type == "once":
                    update_patch["schedule.enabled"] = False
                    update_patch["schedule.next_run"] = None
                collection.update_one(
                    {"_id": scheduled_task["_id"]},
                    {"$set": update_patch, "$inc": {"run_count": 1}}
                )

                # Update in-memory copy
                scheduled_task.setdefault("schedule", {})["next_run"] = next_run_utc
                scheduled_task["last_run"] = now
                scheduled_task["run_count"] = scheduled_task.get("run_count", 0) + 1
                
            except Exception as e:
                logger.error(f"Error executing scheduled task {task_id}: {e}")

    async def _execute_scheduled_task(self, task_id: str, scheduled_task: dict):
        """Execute a scheduled task."""
        try:
            task_data = {
                "goal": scheduled_task["goal"],
                "title": scheduled_task.get("name", scheduled_task["goal"][:50]),
                "conversation_id": scheduled_task.get("conversation_id"),
                "model_name": scheduled_task.get("model_name") or scheduled_task.get("ollama_model_name"),
                "budget": scheduled_task.get("budget"),
                "planner_hints": scheduled_task.get("planner_hints"),
                "status": "PLANNING",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "priority": 1,  # Scheduled tasks get highest priority
            }
            
            new_task_id = create_task(task_data)
            logger.info(f"Executed scheduled task {scheduled_task['name']}, created task {new_task_id}")
            
        except Exception as e:
            logger.error(f"Error executing scheduled task {scheduled_task['name']}: {e}")

# Global scheduler instance
scheduler = TaskScheduler()
