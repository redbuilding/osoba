"""
Tests for Enhanced Heartbeat Features (Phases 1-3)
- Context Gatherer Service
- HEARTBEAT.md File Parser
- Task Creation from Insights
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
import json


class TestContextGatherer:
    """Test context gatherer service."""

    @pytest.mark.asyncio
    async def test_gather_memory_context(self):
        """Test gathering semantic memory context."""
        from services.context_gatherer import ContextGatherer
        
        with patch('db.vector_memory.VectorMemory') as mock_vm:
            mock_vm.return_value.get_stats.return_value = {
                "total_conversations": 100,
                "total_chunks": 500
            }
            
            gatherer = ContextGatherer()
            context = await gatherer.gather_memory_context()
            
            assert context["total_conversations"] == 100
            assert context["total_chunks"] == 500
            assert context["status"] == "healthy"

    def test_gather_git_context_valid_repo(self):
        """Test gathering git context from valid repository."""
        from services.context_gatherer import ContextGatherer
        
        with patch('services.context_gatherer.Path') as mock_path:
            mock_path.return_value.__truediv__.return_value.exists.return_value = True
            
            with patch.object(ContextGatherer, '_run_git_command') as mock_git:
                mock_git.side_effect = [
                    "main",  # branch
                    " M file1.py\n M file2.py",  # status
                    "",  # unpushed (none)
                    "abc123 Recent commit"  # recent commits
                ]
                
                gatherer = ContextGatherer()
                context = gatherer.gather_git_context()
                
                assert context["branch"] == "main"
                assert context["uncommitted_files"] == 2
                assert context["status"] == "dirty"

    def test_gather_git_context_not_a_repo(self):
        """Test gathering git context when not in a repository."""
        from services.context_gatherer import ContextGatherer
        
        with patch('services.context_gatherer.Path') as mock_path:
            mock_path.return_value.__truediv__.return_value.exists.return_value = False
            
            gatherer = ContextGatherer()
            context = gatherer.gather_git_context()
            
            assert context["status"] == "not_a_repo"

    def test_gather_project_context(self):
        """Test gathering project file context."""
        from services.context_gatherer import ContextGatherer
        
        with patch('services.context_gatherer.Path') as mock_path:
            mock_file = MagicMock()
            mock_file.read_text.return_value = "# TODO: Fix this\n# FIXME: Bug here"
            mock_path.return_value.__truediv__.return_value.exists.return_value = True
            mock_path.return_value.__truediv__.return_value.rglob.return_value = [mock_file]
            
            with patch.object(ContextGatherer, '_run_git_command', return_value="file1.py\nfile2.py"):
                gatherer = ContextGatherer()
                context = gatherer.gather_project_context()
                
                assert context["todo_count"] >= 1
                assert context["fixme_count"] >= 1

    def test_gather_system_context(self):
        """Test gathering system health context."""
        from services.context_gatherer import ContextGatherer
        import shutil
        
        with patch.object(shutil, 'disk_usage') as mock_disk:
            mock_disk.return_value = MagicMock(
                free=10 * 1024**3,  # 10 GB
                used=5 * 1024**3,   # 5 GB
                total=15 * 1024**3  # 15 GB
            )
            
            gatherer = ContextGatherer()
            context = gatherer.gather_system_context()
            
            assert context["disk_free_gb"] == 10.0
            assert context["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_gather_all_contexts(self):
        """Test gathering all contexts together."""
        from services.context_gatherer import ContextGatherer
        
        with patch.object(ContextGatherer, 'gather_memory_context', return_value={"status": "healthy"}):
            with patch.object(ContextGatherer, 'gather_git_context', return_value={"status": "clean"}):
                with patch.object(ContextGatherer, 'gather_project_context', return_value={"status": "active"}):
                    with patch.object(ContextGatherer, 'gather_system_context', return_value={"status": "healthy"}):
                        gatherer = ContextGatherer()
                        context = await gatherer.gather_all(
                            include_memory=True,
                            include_git=True,
                            include_project=True,
                            include_system=True
                        )
                        
                        assert "memory" in context
                        assert "git" in context
                        assert "project" in context
                        assert "system" in context


class TestHeartbeatFileParser:
    """Test HEARTBEAT.md file parser."""

    def test_parse_valid_file(self):
        """Test parsing valid HEARTBEAT.md file."""
        from services.heartbeat_file_parser import HeartbeatFileParser
        
        content = """# Heartbeat Tasks

## Memory Management
Schedule: 0 2 * * *
Enabled: true
Prompt: Review semantic memory usage
Context: memory

## Testing Reminders
Schedule: 0 9 * * 1
Enabled: false
Prompt: Check test coverage
Create_Task: true
Context: git,project
"""
        
        with patch('services.heartbeat_file_parser.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.read_text.return_value = content
            
            parser = HeartbeatFileParser("HEARTBEAT.md")
            tasks = parser.parse()
            
            assert len(tasks) == 2
            assert tasks[0]["category"] == "Memory Management"
            assert tasks[0]["schedule"] == "0 2 * * *"
            assert tasks[0]["enabled"] is True
            assert tasks[0]["context_sources"]["memory"] is True
            
            assert tasks[1]["category"] == "Testing Reminders"
            assert tasks[1]["enabled"] is False
            assert tasks[1]["create_task"] is True

    def test_validate_tasks(self):
        """Test task validation."""
        from services.heartbeat_file_parser import HeartbeatFileParser
        
        parser = HeartbeatFileParser()
        
        # Valid task
        valid_task = {
            "category": "Test",
            "schedule": "2h",
            "prompt": "Test prompt"
        }
        errors = parser.validate([valid_task])
        assert len(errors) == 0
        
        # Invalid task (missing prompt)
        invalid_task = {
            "category": "Test",
            "schedule": "2h"
        }
        errors = parser.validate([invalid_task])
        assert len(errors) > 0
        assert "Missing prompt" in errors[0]

    def test_write_tasks_to_file(self):
        """Test writing tasks to HEARTBEAT.md."""
        from services.heartbeat_file_parser import HeartbeatFileParser
        
        tasks = [
            {
                "category": "Test Task",
                "schedule": "2h",
                "enabled": True,
                "prompt": "Test prompt",
                "create_task": False,
                "context_sources": {"memory": True, "git": True, "project": False, "system": False}
            }
        ]
        
        with patch('services.heartbeat_file_parser.Path') as mock_path:
            mock_file = mock_open()
            mock_path.return_value.write_text = mock_file
            
            parser = HeartbeatFileParser()
            result = parser.write(tasks, "test.md")
            
            assert result is True

    def test_file_not_found(self):
        """Test handling when HEARTBEAT.md doesn't exist."""
        from services.heartbeat_file_parser import HeartbeatFileParser
        
        with patch('services.heartbeat_file_parser.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            
            parser = HeartbeatFileParser()
            assert parser.exists() is False
            assert parser.parse() == []


class TestTaskCreationFromInsights:
    """Test task creation from heartbeat insights."""

    @pytest.mark.asyncio
    async def test_create_task_from_insight(self):
        """Test creating a task from an insight."""
        from services.heartbeat_service import HeartbeatService
        
        insight_data = {
            "title": "Test Insight",
            "description": "Test description"
        }
        
        with patch('services.heartbeat_service.create_task') as mock_create:
            mock_create.return_value = "task123"
            
            service = HeartbeatService()
            task_id = await service._create_task_from_insight(
                insight_data, "default", "insight123"
            )
            
            assert task_id == "task123"
            mock_create.assert_called_once()
            call_args = mock_create.call_args[0][0]
            assert call_args["goal"] == "Test Insight"
            assert call_args["metadata"]["source"] == "heartbeat"

    @pytest.mark.asyncio
    async def test_create_task_handles_errors(self):
        """Test task creation error handling."""
        from services.heartbeat_service import HeartbeatService
        
        insight_data = {
            "title": "Test Insight",
            "description": "Test description"
        }
        
        with patch('services.heartbeat_service.create_task', side_effect=Exception("DB error")):
            service = HeartbeatService()
            task_id = await service._create_task_from_insight(
                insight_data, "default", "insight123"
            )
            
            assert task_id is None


class TestEnhancedHeartbeatIntegration:
    """Test integration of enhanced heartbeat features."""

    @pytest.mark.asyncio
    async def test_heartbeat_with_enhanced_context(self):
        """Test heartbeat run with enhanced context gathering."""
        from services.heartbeat_service import HeartbeatService
        
        with patch('services.heartbeat_service.get_user_profile') as mock_profile:
            mock_profile.return_value = {
                "goals_document": "Test goals",
                "heartbeat_config": {
                    "enabled": True,
                    "context_sources": {
                        "memory": True,
                        "git": True,
                        "project": False,
                        "system": False
                    }
                }
            }
            
            with patch('services.heartbeat_service.get_context_gatherer') as mock_gatherer:
                mock_gatherer.return_value.gather_all = AsyncMock(return_value={
                    "memory": {"status": "healthy"},
                    "git": {"status": "clean"}
                })
                
                with patch('services.heartbeat_service.get_all_conversations', return_value=[]):
                    with patch('services.heartbeat_service.list_tasks', return_value=[]):
                        with patch('services.heartbeat_service.chat_with_provider', return_value="HEARTBEAT_OK"):
                            with patch('services.heartbeat_service.count_insights_today', return_value=0):
                                service = HeartbeatService()
                                await service.run_heartbeat("default")
                                
                                # Should complete without errors
                                assert True

    def test_build_prompt_with_enhanced_context(self):
        """Test prompt building includes enhanced context."""
        from services.heartbeat_service import HeartbeatService
        
        context = {
            "goals": "Test goals",
            "recent_conversations": [],
            "active_tasks": [],
            "enhanced_context": {
                "memory": {
                    "total_conversations": 100,
                    "storage_mb": 50,
                    "status": "healthy"
                },
                "git": {
                    "branch": "main",
                    "uncommitted_files": 5,
                    "unpushed_commits": 2,
                    "status": "dirty"
                }
            }
        }
        
        service = HeartbeatService()
        prompt = service._build_prompt(context)
        
        assert "100 conversations indexed" in prompt
        assert "Branch 'main'" in prompt
        assert "5 uncommitted files" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
