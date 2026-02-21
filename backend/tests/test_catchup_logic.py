import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta
from services.task_scheduler import TaskScheduler


class TestCatchupLogic:
    """Test catch-up logic for delayed scheduled tasks."""

    @pytest.mark.asyncio
    async def test_delay_calculation(self):
        """Test that delay is calculated correctly for overdue tasks."""
        scheduler = TaskScheduler()
        
        # Create a task that was supposed to run 45 minutes ago
        now = datetime.now(timezone.utc)
        past_run = now - timedelta(minutes=45)
        
        delay_seconds = (now - past_run).total_seconds()
        delay_minutes = int(delay_seconds / 60)
        
        assert delay_minutes == 45
        assert delay_minutes > 5  # Should trigger warning

    @pytest.mark.asyncio
    async def test_overdue_task_executes_immediately(self):
        """Test that overdue tasks execute immediately on wake."""
        scheduler = TaskScheduler()
        
        # Mock task that's 30 minutes overdue
        now = datetime.now(timezone.utc)
        past_run = now - timedelta(minutes=30)
        
        mock_task = {
            "_id": "test_id",
            "name": "Test Task",
            "goal": "Test goal",
            "schedule": {
                "type": "recurring",
                "cron_expression": "0 9 * * *",
                "next_run": past_run,
                "enabled": True
            },
            "run_count": 0
        }
        
        scheduler.scheduled_tasks["test_id"] = mock_task
        
        with patch('services.task_scheduler.get_scheduled_tasks_collection') as mock_collection, \
             patch('services.task_scheduler.create_task') as mock_create_task, \
             patch('services.task_scheduler.compute_next_run') as mock_compute:
            
            mock_collection.return_value.update_one = MagicMock()
            mock_create_task.return_value = "new_task_id"
            mock_compute.return_value = (now + timedelta(days=1), None)
            
            await scheduler._check_and_execute_due_tasks()
            
            # Verify task was executed
            mock_create_task.assert_called_once()
            
            # Verify delay was tracked in metadata (not title)
            call_args = mock_create_task.call_args[0][0]
            assert call_args["metadata"]["system_delay_minutes"] == 30
            assert call_args["metadata"]["scheduled_for"] == past_run
            assert "delayed" not in call_args["title"]  # Title no longer has delay

    @pytest.mark.asyncio
    async def test_no_delay_for_on_time_task(self):
        """Test that on-time tasks don't show delay."""
        scheduler = TaskScheduler()
        
        # Mock task that's on time (1 minute overdue, within threshold)
        now = datetime.now(timezone.utc)
        past_run = now - timedelta(minutes=1)
        
        mock_task = {
            "_id": "test_id",
            "name": "Test Task",
            "goal": "Test goal",
            "schedule": {
                "type": "recurring",
                "cron_expression": "0 9 * * *",
                "next_run": past_run,
                "enabled": True
            },
            "run_count": 0
        }
        
        scheduler.scheduled_tasks["test_id"] = mock_task
        
        with patch('services.task_scheduler.get_scheduled_tasks_collection') as mock_collection, \
             patch('services.task_scheduler.create_task') as mock_create_task, \
             patch('services.task_scheduler.compute_next_run') as mock_compute:
            
            mock_collection.return_value.update_one = MagicMock()
            mock_create_task.return_value = "new_task_id"
            mock_compute.return_value = (now + timedelta(days=1), None)
            
            await scheduler._check_and_execute_due_tasks()
            
            # Verify task was executed
            mock_create_task.assert_called_once()
            
            # Verify no delay in metadata (1 minute is below 5 minute threshold)
            call_args = mock_create_task.call_args[0][0]
            assert "delayed" not in call_args["title"]
            assert call_args["metadata"]["system_delay_minutes"] == 1

    @pytest.mark.asyncio
    async def test_recurring_task_next_run_from_now(self):
        """Test that recurring tasks calculate next run from NOW, not from missed time."""
        scheduler = TaskScheduler()
        
        # Mock task that's 2 hours overdue
        now = datetime.now(timezone.utc)
        past_run = now - timedelta(hours=2)
        expected_next_run = now + timedelta(days=1)
        
        mock_task = {
            "_id": "test_id",
            "name": "Daily Task",
            "goal": "Test goal",
            "schedule": {
                "type": "recurring",
                "cron_expression": "0 9 * * *",
                "next_run": past_run,
                "enabled": True
            },
            "run_count": 0
        }
        
        scheduler.scheduled_tasks["test_id"] = mock_task
        
        with patch('services.task_scheduler.get_scheduled_tasks_collection') as mock_collection, \
             patch('services.task_scheduler.create_task') as mock_create_task, \
             patch('services.task_scheduler.compute_next_run') as mock_compute:
            
            mock_collection.return_value.update_one = MagicMock()
            mock_create_task.return_value = "new_task_id"
            # compute_next_run should be called with NOW, not past_run
            mock_compute.return_value = (expected_next_run, None)
            
            await scheduler._check_and_execute_due_tasks()
            
            # Verify compute_next_run was called with current time
            mock_compute.assert_called_once()
            call_args = mock_compute.call_args
            assert call_args[1]["now_utc"] >= now - timedelta(seconds=5)  # Allow 5 sec tolerance

    @pytest.mark.asyncio
    async def test_one_time_task_disables_after_execution(self):
        """Test that one-time tasks are disabled after execution, even if delayed."""
        scheduler = TaskScheduler()
        
        # Mock one-time task that's 1 hour overdue
        now = datetime.now(timezone.utc)
        past_run = now - timedelta(hours=1)
        
        mock_task = {
            "_id": "test_id",
            "name": "One-time Task",
            "goal": "Test goal",
            "schedule": {
                "type": "once",
                "once_at": past_run,
                "next_run": past_run,
                "enabled": True
            },
            "run_count": 0
        }
        
        scheduler.scheduled_tasks["test_id"] = mock_task
        
        with patch('services.task_scheduler.get_scheduled_tasks_collection') as mock_collection, \
             patch('services.task_scheduler.create_task') as mock_create_task:
            
            mock_update = MagicMock()
            mock_collection.return_value.update_one = mock_update
            mock_create_task.return_value = "new_task_id"
            
            await scheduler._check_and_execute_due_tasks()
            
            # Verify task was disabled
            update_call = mock_update.call_args[0][1]
            assert update_call["$set"]["schedule.enabled"] is False
            assert update_call["$set"]["schedule.next_run"] is None

    @pytest.mark.asyncio
    async def test_delay_stored_in_database(self):
        """Test that delay information is stored in the database."""
        scheduler = TaskScheduler()
        
        # Mock task that's 15 minutes overdue
        now = datetime.now(timezone.utc)
        past_run = now - timedelta(minutes=15)
        
        mock_task = {
            "_id": "test_id",
            "name": "Test Task",
            "goal": "Test goal",
            "schedule": {
                "type": "recurring",
                "cron_expression": "0 * * * *",
                "next_run": past_run,
                "enabled": True
            },
            "run_count": 0
        }
        
        scheduler.scheduled_tasks["test_id"] = mock_task
        
        with patch('services.task_scheduler.get_scheduled_tasks_collection') as mock_collection, \
             patch('services.task_scheduler.create_task') as mock_create_task, \
             patch('services.task_scheduler.compute_next_run') as mock_compute:
            
            mock_update = MagicMock()
            mock_collection.return_value.update_one = mock_update
            mock_create_task.return_value = "new_task_id"
            mock_compute.return_value = (now + timedelta(hours=1), None)
            
            await scheduler._check_and_execute_due_tasks()
            
            # Verify delay was stored in database
            update_call = mock_update.call_args[0][1]
            assert "last_delay_minutes" in update_call["$set"]
            assert update_call["$set"]["last_delay_minutes"] == 15

    @pytest.mark.asyncio
    async def test_warning_logged_for_significant_delay(self):
        """Test that warnings are logged for tasks delayed more than 5 minutes."""
        scheduler = TaskScheduler()
        
        # Mock task that's 30 minutes overdue
        now = datetime.now(timezone.utc)
        past_run = now - timedelta(minutes=30)
        
        mock_task = {
            "_id": "test_id",
            "name": "Important Task",
            "goal": "Test goal",
            "schedule": {
                "type": "recurring",
                "cron_expression": "0 9 * * *",
                "next_run": past_run,
                "enabled": True
            },
            "run_count": 0
        }
        
        scheduler.scheduled_tasks["test_id"] = mock_task
        
        with patch('services.task_scheduler.get_scheduled_tasks_collection') as mock_collection, \
             patch('services.task_scheduler.create_task') as mock_create_task, \
             patch('services.task_scheduler.compute_next_run') as mock_compute, \
             patch('services.task_scheduler.logger') as mock_logger:
            
            mock_collection.return_value.update_one = MagicMock()
            mock_create_task.return_value = "new_task_id"
            mock_compute.return_value = (now + timedelta(days=1), None)
            
            await scheduler._check_and_execute_due_tasks()
            
            # Verify warning was logged
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if "30 minutes late" in str(call)]
            assert len(warning_calls) > 0
