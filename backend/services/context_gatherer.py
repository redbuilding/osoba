"""
Context Gatherer Service for Enhanced Heartbeat

Collects rich context from multiple sources:
- Semantic memory statistics and recent activity
- Git repository status and changes
- Project file activity and TODO comments
- System health metrics
"""

import os
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ContextGatherer:
    """Gathers context from various sources for heartbeat insights"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.getcwd()
    
    async def gather_all(
        self,
        include_memory: bool = True,
        include_git: bool = True,
        include_project: bool = False,
        include_system: bool = False
    ) -> Dict[str, Any]:
        """Gather context from all enabled sources"""
        context = {}
        
        if include_memory:
            context["memory"] = await self.gather_memory_context()
        
        if include_git:
            context["git"] = self.gather_git_context()
        
        if include_project:
            context["project"] = self.gather_project_context()
        
        if include_system:
            context["system"] = self.gather_system_context()
        
        return context
    
    async def gather_memory_context(self) -> Dict[str, Any]:
        """Gather semantic memory statistics and recent activity"""
        try:
            from db.vector_memory import get_vector_memory
            
            vm = get_vector_memory()
            stats = vm.get_stats()
            
            # Get recent searches from memory (if available)
            recent_searches = []
            # TODO: Track searches in a separate collection if needed
            
            return {
                "total_conversations": stats.get("total_conversations", 0),
                "total_chunks": stats.get("total_chunks", 0),
                "storage_mb": round(stats.get("total_chunks", 0) * 0.5 / 1024, 2),  # Estimate
                "recent_searches": recent_searches,
                "status": "healthy" if stats.get("total_conversations", 0) > 0 else "empty"
            }
        except Exception as e:
            logger.warning(f"Failed to gather memory context: {e}")
            return {"status": "unavailable", "error": str(e)}
    
    def gather_git_context(self) -> Dict[str, Any]:
        """Gather git repository status and changes"""
        try:
            # Check if git repo exists
            git_dir = Path(self.project_root) / ".git"
            if not git_dir.exists():
                return {"status": "not_a_repo"}
            
            # Get current branch
            branch = self._run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            
            # Get uncommitted files
            status_output = self._run_git_command(["git", "status", "--porcelain"])
            uncommitted_files = len([line for line in status_output.split("\n") if line.strip()])
            
            # Get unpushed commits
            try:
                unpushed = self._run_git_command(["git", "log", "@{u}..", "--oneline"])
                unpushed_commits = len([line for line in unpushed.split("\n") if line.strip()])
            except Exception:
                unpushed_commits = 0
            
            # Get recent commits (last 5)
            recent_commits = self._run_git_command([
                "git", "log", "-5", "--pretty=format:%h %s"
            ])
            
            return {
                "branch": branch.strip(),
                "uncommitted_files": uncommitted_files,
                "unpushed_commits": unpushed_commits,
                "recent_commits": [c for c in recent_commits.split("\n") if c.strip()],
                "status": "dirty" if uncommitted_files > 0 else "clean"
            }
        except Exception as e:
            logger.warning(f"Failed to gather git context: {e}")
            return {"status": "unavailable", "error": str(e)}
    
    def gather_project_context(self) -> Dict[str, Any]:
        """Gather project file activity and TODO comments"""
        try:
            # Find TODO/FIXME comments
            todo_count = 0
            fixme_count = 0
            recent_files = []
            
            # Search common code directories
            search_dirs = ["backend", "frontend/src", "src"]
            for dir_name in search_dirs:
                dir_path = Path(self.project_root) / dir_name
                if dir_path.exists():
                    for file_path in dir_path.rglob("*.py"):
                        try:
                            content = file_path.read_text()
                            todo_count += content.count("TODO")
                            fixme_count += content.count("FIXME")
                        except Exception:
                            pass
            
            # Get recently modified files (last 24 hours)
            try:
                recent_output = self._run_git_command([
                    "git", "log", "--since=24 hours ago", "--name-only", "--pretty=format:"
                ])
                recent_files = list(set([f for f in recent_output.split("\n") if f.strip()]))[:10]
            except Exception:
                recent_files = []
            
            return {
                "todo_count": todo_count,
                "fixme_count": fixme_count,
                "recent_files": recent_files,
                "status": "active" if recent_files else "idle"
            }
        except Exception as e:
            logger.warning(f"Failed to gather project context: {e}")
            return {"status": "unavailable", "error": str(e)}
    
    def gather_system_context(self) -> Dict[str, Any]:
        """Gather system health metrics"""
        try:
            # Get disk usage for project directory
            import shutil
            disk_usage = shutil.disk_usage(self.project_root)
            
            # Check if services are running (basic check)
            services_status = {
                "mongodb": self._check_service_port(27017),
                "ollama": self._check_service_port(11434),
            }
            
            return {
                "disk_free_gb": round(disk_usage.free / (1024**3), 2),
                "disk_used_percent": round(disk_usage.used / disk_usage.total * 100, 1),
                "services": services_status,
                "status": "healthy"
            }
        except Exception as e:
            logger.warning(f"Failed to gather system context: {e}")
            return {"status": "unavailable", "error": str(e)}
    
    def _run_git_command(self, cmd: List[str]) -> str:
        """Run a git command and return output"""
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout
    
    def _check_service_port(self, port: int) -> bool:
        """Check if a service is listening on a port"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                return s.connect_ex(("localhost", port)) == 0
        except Exception:
            return False


# Singleton instance
_context_gatherer: Optional[ContextGatherer] = None


def get_context_gatherer() -> ContextGatherer:
    """Get or create the context gatherer singleton"""
    global _context_gatherer
    if _context_gatherer is None:
        _context_gatherer = ContextGatherer()
    return _context_gatherer
