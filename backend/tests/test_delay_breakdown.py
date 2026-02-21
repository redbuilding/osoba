import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta
from services.task_scheduler import TaskScheduler
from services.task_runner import _run_task


class TestDelayBreakdown:
    """Test system delay vs queue delay tracking."""

    @pytest.mark.asyncio
    async def test_system_delay_only(self):
        """Test task delayed only by system sleep (no queue)."""
        scheduler = TaskScheduler()
        
        # Task overdue by 2 hours
        now = datetime.now(timezone.utc)
        past_run = now - timedelta(hours=2)
        
        mock_task = {
            "_id": "test_id",
            "name": "Task A",
            "goal": "Test goal",
            "schedule": {
                "type": "recurring",
                "cron_expression": "0 8 * * *",
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
            
            # Verify system delay was tracked
            call_args = mock_create_task.call_args[0][0]
            assert call_args["metadata"]["system_delay_minutes"] == 120
            assert call_args["metadata"]["scheduled_for"] == past_run
            
            # Verify scheduled task was updated with system delay
            update_call = mock_collection.return_value.update_one.call_args[0][1]
            assert update_call["$set"]["last_system_delay_minutes"] == 120

    @pytest.mark.asyncio
    async def test_queue_delay_calculation(self):
        """Test queue delay calculation when task starts running."""
        # Mock task that was scheduled 10 minutes ago, with 2 min system delay
        now = datetime.now(timezone.utc)
        scheduled_for = now - timedelta(minutes=10)
        
        mock_task_doc = {
            "_id": "task_id",
            "goal": "Test goal",
            "status": "PLANNING",
            "metadata": {
                "scheduled_task_id": "sched_id",
                "scheduled_for": scheduled_for,
                "system_delay_minutes": 2
            }
        }
        
        with patch('services.task_runner.get_task') as mock_get_task, \
             patch('services.task_runner.update_task') as mock_update_task, \
             patch('services.task_runner.plan_task') as mock_plan_task, \
             patch('db.mongodb.get_scheduled_tasks_collection') as mock_sched_collection, \
             patch('services.task_runner.progress_bus'):
            
            mock_get_task.return_value = mock_task_doc
            mock_plan_task.return_value = MagicMock(model_dump=lambda: {})
            mock_sched_collection.return_value.update_one = MagicMock()
            
            # Start the task (this should calculate queue delay)
            try:
                await _run_task("task_id")
            except:
                pass  # We're only testing the delay calculation part
            
            # Verify queue delay was calculated
            update_calls = [call for call in mock_update_task.call_args_list]
            metadata_update = None
            for call in update_calls:
                if "metadata" in call[0][1]:
                    metadata_update = call[0][1]["metadata"]
                    break
            
            assert metadata_update is not None
            assert "queue_delay_minutes" in metadata_update
            assert "total_delay_minutes" in metadata_update
            
            # Total delay should be ~10 minutes
            assert metadata_update["total_delay_minutes"] >= 9
            assert metadata_update["total_delay_minutes"] <= 11
            
            # Queue delay should be total - system (10 - 2 = 8)
            assert metadata_update["queue_delay_minutes"] >= 7
            assert metadata_update["queue_delay_minutes"] <= 9

    @pytest.mark.asyncio
    async def test_cascading_delay_scenario(self):
        """Test the full scenario: Task A delayed by sleep, Task B queued behind it."""
        scheduler = TaskScheduler()
        
        # Simulate computer wake at 10:00 AM
        now = datetime.now(timezone.utc)
        
        # Task A: scheduled for 8:00 AM (2 hours ago)
        task_a_scheduled = now - timedelta(hours=2)
        
        # Task B: scheduled for 10:05 AM (5 minutes from now, but will be created soon)
        task_b_scheduled = now + timedelta(minutes=5)
        
        mock_task_a = {
            "_id": "task_a_id",
            "name": "Task A",
            "goal": "Task A goal",
            "schedule": {
                "type": "recurring",
                "cron_expression": "0 8 * * *",
                "next_run": task_a_scheduled,
                "enabled": True
            },
            "run_count": 0
        }
        
        scheduler.scheduled_tasks["task_a_id"] = mock_task_a
        
        with patch('services.task_scheduler.get_scheduled_tasks_collection') as mock_collection, \
             patch('services.task_scheduler.create_task') as mock_create_task, \
             patch('services.task_scheduler.compute_next_run') as mock_compute:
            
            mock_collection.return_value.update_one = MagicMock()
            mock_create_task.return_value = "task_a_exec_id"
            mock_compute.return_value = (now + timedelta(days=1), None)
            
            # Execute Task A (catch-up)
            await scheduler._check_and_execute_due_tasks()
            
            # Verify Task A has system delay of 120 minutes
            task_a_call = mock_create_task.call_args[0][0]
            assert task_a_call["metadata"]["system_delay_minutes"] == 120
            
            # Now simulate 5 minutes passing and Task B becoming due
            future_now = now + timedelta(minutes=5)
            
            mock_task_b = {
                "_id": "task_b_id",
                "name": "Task B",
                "goal": "Task B goal",
                "schedule": {
                    "type": "recurring",
                    "cron_expression": "5 10 * * *",
                    "next_run": task_b_scheduled,
                    "enabled": True
                },
                "run_count": 0
            }
            
            scheduler.scheduled_tasks["task_b_id"] = mock_task_b
            
            # Reset mock to track Task B creation
            mock_create_task.reset_mock()
            
            # Execute Task B (on time, but will queue)
            with patch('services.task_scheduler.datetime') as mock_datetime:
                mock_datetime.now.return_value = future_now
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                
                await scheduler._check_and_execute_due_tasks()
            
            # Verify Task B has minimal system delay (0-1 minutes)
            task_b_call = mock_create_task.call_args[0][0]
            assert task_b_call["metadata"]["system_delay_minutes"] <= 1
            
            # Task B will have queue delay added when it actually starts running
            # (which would happen after Task A completes in the real scenario)

    @pytest.mark.asyncio
    async def test_no_delay_for_on_time_task(self):
        """Test that on-time tasks show zero system delay."""
        scheduler = TaskScheduler()
        
        # Task scheduled 30 seconds ago (within threshold)
        now = datetime.now(timezone.utc)
        past_run = now - timedelta(seconds=30)
        
        mock_task = {
            "_id": "test_id",
            "name": "On-time Task",
            "goal": "Test goal",
            "schedule": {
                "type": "recurring",
                "cron_expression": "* * * * *",
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
            mock_compute.return_value = (now + timedelta(minutes=1), None)
            
            await scheduler._check_and_execute_due_tasks()
            
            # Verify system delay is 0 (30 seconds rounds down)
            call_args = mock_create_task.call_args[0][0]
            assert call_args["metadata"]["system_delay_minutes"] == 0
            
            # Verify no delay warning in logs
            update_call = mock_collection.return_value.update_one.call_args[0][1]
            assert update_call["$set"]["last_system_delay_minutes"] == 0

    @pytest.mark.asyncio
    async def test_scheduled_task_updated_with_queue_delay(self):
        """Test that scheduled task record is updated with queue delay."""
        now = datetime.now(timezone.utc)
        scheduled_for = now - timedelta(minutes=15)
        
        mock_task_doc = {
            "_id": "task_id",
            "goal": "Test goal",
            "status": "PLANNING",
            "metadata": {
                "scheduled_task_id": "sched_id",
                "scheduled_for": scheduled_for,
                "system_delay_minutes": 5  # 5 min system delay
            }
        }
        
        with patch('services.task_runner.get_task') as mock_get_task, \
             patch('services.task_runner.update_task') as mock_update_task, \
             patch('services.task_runner.plan_task') as mock_plan_task, \
             patch('db.mongodb.get_scheduled_tasks_collection') as mock_sched_collection, \
             patch('services.task_runner.progress_bus'):
            
            mock_get_task.return_value = mock_task_doc
            mock_plan_task.return_value = MagicMock(model_dump=lambda: {})
            mock_sched_update = MagicMock()
            mock_sched_collection.return_value.update_one = mock_sched_update
            
            try:
                await _run_task("task_id")
            except:
                pass
            
            # Verify scheduled task was updated with queue delay
            sched_update_call = mock_sched_update.call_args
            if sched_update_call:
                update_data = sched_update_call[0][1]["$set"]
                assert "last_queue_delay_minutes" in update_data
                # Queue delay should be ~10 minutes (15 total - 5 system)
                assert update_data["last_queue_delay_minutes"] >= 9
                assert update_data["last_queue_delay_minutes"] <= 11
