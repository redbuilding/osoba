import asyncio
import re
from datetime import datetime, timezone, time as dt_time
from typing import Optional, Dict, Any, List
from zoneinfo import ZoneInfo

from services.provider_service import chat_with_provider
from services.context_service import get_user_context
from services.context_gatherer import get_context_gatherer
from db.heartbeat_crud import create_insight, count_insights_today
from db.user_profiles_crud import get_user_profile
from db.crud import get_all_conversations
from db.tasks_crud import list_tasks, create_task
from core.config import get_logger

logger = get_logger("heartbeat_service")


class HeartbeatService:
    """Background service that runs periodic heartbeats for proactive insights."""
    
    def __init__(self):
        self.running = False
        self._task = None
        self.check_interval = 300  # Check every 5 minutes
        self.last_run_times: Dict[str, datetime] = {}  # user_id -> last run time
    
    async def start(self):
        """Start the heartbeat service."""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info("Heartbeat service started")
    
    async def stop(self):
        """Stop the heartbeat service."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Heartbeat service stopped")
    
    async def _heartbeat_loop(self):
        """Main heartbeat loop that checks and runs heartbeats."""
        while self.running:
            try:
                # For now, only check default user
                # In production, iterate through all users with heartbeat enabled
                await self._check_and_run_heartbeat("default")
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)
    
    async def _check_and_run_heartbeat(self, user_id: str):
        """Check if heartbeat is due and run it if needed."""
        try:
            profile = get_user_profile(user_id)
            if not profile:
                return
            
            config = profile.get("heartbeat_config", {})
            if not config.get("enabled", True):
                return
            
            # Check if heartbeat is due
            if not self._is_heartbeat_due(user_id, config):
                return
            
            # Run the heartbeat
            await self.run_heartbeat(user_id)
            
            # Update last run time
            self.last_run_times[user_id] = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error checking heartbeat for {user_id}: {e}", exc_info=True)
    
    def _is_heartbeat_due(self, user_id: str, config: Dict[str, Any]) -> bool:
        """Check if a heartbeat is due for a user."""
        # Get last run time
        last_run = self.last_run_times.get(user_id)
        if not last_run:
            # First run
            return True
        
        # Parse interval
        interval_seconds = self._parse_interval(config.get("interval", "2h"))
        now = datetime.now(timezone.utc)
        
        # Check if enough time has passed
        if (now - last_run).total_seconds() < interval_seconds:
            return False
        
        # Check active hours
        active_hours = config.get("active_hours")
        if active_hours and not self._in_active_hours(active_hours, now):
            return False
        
        return True
    
    def _parse_interval(self, interval_str: str) -> int:
        """Parse interval string (e.g., '2h', '30m') to seconds."""
        match = re.match(r'^(\d+)([hm])$', interval_str.lower())
        if not match:
            logger.warning(f"Invalid interval format: {interval_str}, using default 2h")
            return 7200  # Default 2 hours
        
        value, unit = match.groups()
        value = int(value)
        
        if unit == 'h':
            return value * 3600
        elif unit == 'm':
            return value * 60
        
        return 7200  # Default 2 hours
    
    def _in_active_hours(self, active_hours: Dict[str, Any], now: datetime) -> bool:
        """Check if current time is within active hours."""
        try:
            start_str = active_hours.get("start", "00:00")
            end_str = active_hours.get("end", "24:00")
            tz_str = active_hours.get("timezone")
            
            # Parse times
            start_hour, start_min = map(int, start_str.split(":"))
            end_hour, end_min = map(int, end_str.split(":"))
            
            # Convert to timezone if specified
            if tz_str:
                try:
                    tz = ZoneInfo(tz_str)
                    now = now.astimezone(tz)
                except Exception as e:
                    logger.warning(f"Invalid timezone {tz_str}: {e}")
            
            # Create time objects
            start_time = dt_time(start_hour, start_min)
            end_time = dt_time(end_hour if end_hour < 24 else 23, end_min if end_hour < 24 else 59)
            current_time = now.time()
            
            # Check if current time is within range
            if start_time <= end_time:
                return start_time <= current_time <= end_time
            else:
                # Handles overnight ranges
                return current_time >= start_time or current_time <= end_time
                
        except Exception as e:
            logger.error(f"Error checking active hours: {e}")
            return True  # Default to allowing heartbeat
    
    async def run_heartbeat(self, user_id: str = "default"):
        """Run a heartbeat for a user."""
        try:
            logger.info(f"Running heartbeat for user {user_id}")
            
            # Get user profile and config
            profile = get_user_profile(user_id)
            if not profile:
                logger.warning(f"No profile found for user {user_id}")
                return
            
            config = profile.get("heartbeat_config", {})
            
            # Check daily limit
            max_insights = config.get("max_insights_per_day", 5)
            today_count = count_insights_today(user_id)
            if today_count >= max_insights:
                logger.info(f"Daily insight limit reached for {user_id} ({today_count}/{max_insights})")
                return
            
            # Gather context
            context = await self._gather_context(user_id, profile)
            
            # Build prompt
            prompt = self._build_prompt(context)
            
            # Call LLM
            model_name = config.get("model_name", "anthropic/claude-haiku-4-5")
            messages = [{"role": "user", "content": prompt}]
            
            response = await chat_with_provider(messages, model_name)
            
            if not response:
                logger.warning(f"No response from LLM for heartbeat {user_id}")
                return
            
            # Check for HEARTBEAT_OK
            if self._is_heartbeat_ok(response):
                logger.info(f"Heartbeat OK for {user_id}, no insights needed")
                return
            
            # Create insight
            insight_data = self._parse_insight(response)
            created_insight = create_insight(insight_data, user_id)
            
            if created_insight:
                logger.info(f"Created insight for {user_id}: {insight_data['title']}")
                
                # Optionally create task if configured
                create_task_enabled = config.get("create_task", False)
                if create_task_enabled:
                    task_id = await self._create_task_from_insight(insight_data, user_id, created_insight.get("_id"))
                    if task_id:
                        logger.info(f"Created task {task_id} from insight")
            else:
                logger.error(f"Failed to create insight for {user_id}")
                
        except Exception as e:
            logger.error(f"Error running heartbeat for {user_id}: {e}", exc_info=True)
    
    async def _create_task_from_insight(self, insight_data: Dict[str, Any], user_id: str, insight_id: str) -> Optional[str]:
        """Create a task from a heartbeat insight."""
        try:
            from datetime import datetime, timezone
            from db.heartbeat_crud import get_heartbeat_config
            
            # Get heartbeat config for model selection
            heartbeat_config = get_heartbeat_config(user_id)
            model_name = heartbeat_config.get("model_name") if heartbeat_config else None
            
            goal = insight_data["title"]
            task_data = {
                "title": goal[:60],
                "goal": goal,
                "status": "PLANNING",
                "priority": 2,
                "budget": {},
                "usage": {"tool_calls": 0, "seconds_elapsed": 0},
                "current_step_index": -1,
                "model_name": model_name,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "metadata": {
                    "source": "heartbeat",
                    "insight_id": str(insight_id),
                    "description": insight_data.get("description", "")
                }
            }
            
            task_id = create_task(task_data)
            return task_id
        except Exception as e:
            logger.error(f"Error creating task from insight: {e}")
            return None
    
    async def _gather_context(self, user_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Gather context for heartbeat prompt."""
        context = {
            "goals": profile.get("goals_document", ""),
            "recent_conversations": [],
            "active_tasks": [],
            "enhanced_context": {}
        }
        
        # Get enhanced context from context gatherer
        try:
            config = profile.get("heartbeat_config", {})
            context_config = config.get("context_sources", {
                "memory": True,
                "git": True,
                "project": False,
                "system": False
            })
            
            gatherer = get_context_gatherer()
            enhanced = await gatherer.gather_all(
                include_memory=context_config.get("memory", True),
                include_git=context_config.get("git", True),
                include_project=context_config.get("project", False),
                include_system=context_config.get("system", False)
            )
            context["enhanced_context"] = enhanced
        except Exception as e:
            logger.error(f"Error gathering enhanced context: {e}")
        
        # Get recent conversations (last 3)
        try:
            all_convos = get_all_conversations()
            user_convos = [c for c in all_convos if c.get("user_id", "default") == user_id]
            recent = sorted(user_convos, key=lambda x: x.get("updated_at", datetime.min), reverse=True)[:3]
            
            for convo in recent:
                title = convo.get("title", "Untitled")
                summary = convo.get("summary", "")
                context["recent_conversations"].append({
                    "title": title,
                    "summary": summary[:200] if summary else ""
                })
        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
        
        # Get active tasks
        try:
            tasks = list_tasks(limit=10)
            active = [t for t in tasks if t.get("status") in ["PLANNING", "EXECUTING", "PAUSED"]]
            
            for task in active[:5]:
                context["active_tasks"].append({
                    "title": task.get("title", ""),
                    "status": task.get("status", ""),
                    "goal": task.get("goal", "")[:100]
                })
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
        
        return context
    
    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Build the heartbeat prompt."""
        prompt_parts = [
            "You are a proactive AI assistant reviewing the user's recent activity and goals.",
            "Your task is to identify 1-2 actionable next steps that would help advance their objectives.",
            ""
        ]
        
        # Add goals if present
        if context["goals"]:
            prompt_parts.append("USER GOALS:")
            prompt_parts.append(context["goals"])
            prompt_parts.append("")
        
        # Add enhanced context
        enhanced = context.get("enhanced_context", {})
        if enhanced:
            prompt_parts.append("PROJECT CONTEXT:")
            
            # Memory context
            if "memory" in enhanced and enhanced["memory"].get("status") != "unavailable":
                mem = enhanced["memory"]
                prompt_parts.append(f"- Semantic Memory: {mem.get('total_conversations', 0)} conversations indexed, {mem.get('storage_mb', 0)}MB")
            
            # Git context
            if "git" in enhanced and enhanced["git"].get("status") != "unavailable":
                git = enhanced["git"]
                prompt_parts.append(f"- Git: Branch '{git.get('branch', 'unknown')}', {git.get('uncommitted_files', 0)} uncommitted files, {git.get('unpushed_commits', 0)} unpushed commits")
                if git.get("recent_commits"):
                    prompt_parts.append(f"  Recent commits: {', '.join(git['recent_commits'][:3])}")
            
            # Project context
            if "project" in enhanced and enhanced["project"].get("status") != "unavailable":
                proj = enhanced["project"]
                prompt_parts.append(f"- Project: {proj.get('todo_count', 0)} TODOs, {proj.get('fixme_count', 0)} FIXMEs")
                if proj.get("recent_files"):
                    prompt_parts.append(f"  Recently modified: {', '.join(proj['recent_files'][:5])}")
            
            # System context
            if "system" in enhanced and enhanced["system"].get("status") != "unavailable":
                sys = enhanced["system"]
                prompt_parts.append(f"- System: {sys.get('disk_free_gb', 0)}GB free, {sys.get('disk_used_percent', 0)}% used")
            
            prompt_parts.append("")
        
        # Add recent conversations
        if context["recent_conversations"]:
            prompt_parts.append("RECENT CONVERSATIONS:")
            for i, convo in enumerate(context["recent_conversations"], 1):
                prompt_parts.append(f"{i}. {convo['title']}")
                if convo['summary']:
                    prompt_parts.append(f"   Summary: {convo['summary']}")
            prompt_parts.append("")
        
        # Add active tasks
        if context["active_tasks"]:
            prompt_parts.append("ACTIVE TASKS:")
            for i, task in enumerate(context["active_tasks"], 1):
                prompt_parts.append(f"{i}. {task['title']} (Status: {task['status']})")
                if task['goal']:
                    prompt_parts.append(f"   Goal: {task['goal']}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "Based on this context, suggest 1-2 specific, actionable next steps.",
            "If nothing needs immediate attention, reply with exactly: HEARTBEAT_OK",
            "",
            "Format your response as:",
            "Title: [Brief title]",
            "Description: [Specific action to take]"
        ])
        
        return "\n".join(prompt_parts)
    
    def _is_heartbeat_ok(self, response: str) -> bool:
        """Check if response indicates no action needed."""
        response_clean = response.strip().upper()
        # Check if HEARTBEAT_OK appears at start or end
        return response_clean.startswith("HEARTBEAT_OK") or response_clean.endswith("HEARTBEAT_OK")
    
    def _parse_insight(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into insight data."""
        # Simple parsing - look for Title: and Description:
        title = "Proactive Suggestion"
        description = response
        
        lines = response.split("\n")
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("title:"):
                title = line.split(":", 1)[1].strip()
            elif line.strip().lower().startswith("description:"):
                # Get description and any following lines
                desc_lines = [line.split(":", 1)[1].strip()]
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and not lines[j].strip().lower().startswith("title:"):
                        desc_lines.append(lines[j].strip())
                description = " ".join(desc_lines)
                break
        
        return {
            "insight_type": "task_suggestion",
            "title": title[:200],  # Enforce max length
            "description": description[:1000]  # Enforce max length
        }


# Global instance
heartbeat_service = HeartbeatService()
