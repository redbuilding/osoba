"""
HEARTBEAT.md File Parser

Parses markdown-based heartbeat task definitions for power users.
Supports category-based tasks with schedules, prompts, and configuration.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class HeartbeatFileParser:
    """Parser for HEARTBEAT.md file format"""
    
    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path or self._find_heartbeat_file()
    
    def _find_heartbeat_file(self) -> Optional[str]:
        """Find HEARTBEAT.md in common locations"""
        search_paths = [
            Path(".heartbeat/HEARTBEAT.md"),
            Path("HEARTBEAT.md"),
            Path(".kiro/HEARTBEAT.md")
        ]
        
        for path in search_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def exists(self) -> bool:
        """Check if HEARTBEAT.md file exists"""
        return self.file_path is not None and Path(self.file_path).exists()
    
    def parse(self) -> List[Dict[str, Any]]:
        """Parse HEARTBEAT.md file into task definitions"""
        if not self.exists():
            return []
        
        try:
            content = Path(self.file_path).read_text()
            return self._parse_content(content)
        except Exception as e:
            logger.error(f"Error parsing HEARTBEAT.md: {e}")
            return []
    
    def _parse_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse markdown content into task definitions"""
        tasks = []
        current_task = None
        
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and main title
            if not line or line.startswith("# Heartbeat"):
                continue
            
            # New task (## heading)
            if line.startswith("## "):
                if current_task:
                    tasks.append(current_task)
                
                category = line[3:].strip()
                current_task = {
                    "category": category,
                    "schedule": None,
                    "enabled": True,
                    "prompt": "",
                    "create_task": False,
                    "context_sources": {
                        "memory": True,
                        "git": True,
                        "project": False,
                        "system": False
                    }
                }
            
            # Parse fields
            elif current_task:
                if line.lower().startswith("schedule:"):
                    current_task["schedule"] = line.split(":", 1)[1].strip()
                
                elif line.lower().startswith("enabled:"):
                    value = line.split(":", 1)[1].strip().lower()
                    current_task["enabled"] = value in ["true", "yes", "1"]
                
                elif line.lower().startswith("prompt:"):
                    current_task["prompt"] = line.split(":", 1)[1].strip()
                
                elif line.lower().startswith("create_task:"):
                    value = line.split(":", 1)[1].strip().lower()
                    current_task["create_task"] = value in ["true", "yes", "1"]
                
                elif line.lower().startswith("context:"):
                    # Parse context sources: memory,git,project
                    sources = line.split(":", 1)[1].strip().lower().split(",")
                    current_task["context_sources"] = {
                        "memory": "memory" in sources,
                        "git": "git" in sources,
                        "project": "project" in sources,
                        "system": "system" in sources
                    }
        
        # Add last task
        if current_task:
            tasks.append(current_task)
        
        return tasks
    
    def validate(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """Validate parsed tasks and return list of errors"""
        errors = []
        
        for i, task in enumerate(tasks):
            task_id = f"Task {i+1} ({task.get('category', 'Unknown')})"
            
            # Check required fields
            if not task.get("category"):
                errors.append(f"{task_id}: Missing category name")
            
            if not task.get("schedule"):
                errors.append(f"{task_id}: Missing schedule")
            
            if not task.get("prompt"):
                errors.append(f"{task_id}: Missing prompt")
            
            # Validate schedule format (basic check)
            schedule = task.get("schedule", "")
            if schedule and not self._is_valid_schedule(schedule):
                errors.append(f"{task_id}: Invalid schedule format '{schedule}'")
        
        return errors
    
    def _is_valid_schedule(self, schedule: str) -> bool:
        """Basic validation of schedule format"""
        # Support cron format or interval format (e.g., "2h", "30m")
        cron_pattern = r'^[\d\*\-,/\s]+$'
        interval_pattern = r'^\d+[hm]$'
        
        return bool(re.match(cron_pattern, schedule)) or bool(re.match(interval_pattern, schedule))
    
    def write(self, tasks: List[Dict[str, Any]], file_path: Optional[str] = None) -> bool:
        """Write tasks to HEARTBEAT.md file"""
        try:
            output_path = file_path or self.file_path or "HEARTBEAT.md"
            content = self._generate_content(tasks)
            
            Path(output_path).write_text(content)
            logger.info(f"Wrote {len(tasks)} tasks to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing HEARTBEAT.md: {e}")
            return False
    
    def _generate_content(self, tasks: List[Dict[str, Any]]) -> str:
        """Generate markdown content from task definitions"""
        lines = [
            "# Heartbeat Tasks",
            "",
            "# Define automated heartbeat tasks with schedules and prompts.",
            "# Format:",
            "# ## Category Name",
            "# Schedule: <cron or interval>",
            "# Enabled: true|false",
            "# Prompt: <task prompt>",
            "# Create_Task: true|false (optional, creates tracked task)",
            "# Context: memory,git,project,system (optional, comma-separated)",
            ""
        ]
        
        for task in tasks:
            lines.append(f"## {task.get('category', 'Unnamed')}")
            lines.append(f"Schedule: {task.get('schedule', '2h')}")
            lines.append(f"Enabled: {str(task.get('enabled', True)).lower()}")
            lines.append(f"Prompt: {task.get('prompt', '')}")
            
            if task.get("create_task"):
                lines.append(f"Create_Task: true")
            
            # Add context sources if not default
            context = task.get("context_sources", {})
            if context != {"memory": True, "git": True, "project": False, "system": False}:
                sources = [k for k, v in context.items() if v]
                if sources:
                    lines.append(f"Context: {','.join(sources)}")
            
            lines.append("")
        
        return "\n".join(lines)


# Singleton instance
_parser: Optional[HeartbeatFileParser] = None


def get_heartbeat_file_parser() -> HeartbeatFileParser:
    """Get or create the heartbeat file parser singleton"""
    global _parser
    if _parser is None:
        _parser = HeartbeatFileParser()
    return _parser
