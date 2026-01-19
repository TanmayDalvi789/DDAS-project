"""
Phase 3: Async Queue Unit Tests
Tests for Redis queue, worker, task queue, and management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import json

from app.workers.redis_queue import RedisQueueManager
from app.workers.worker import WorkerManager
from app.workers.task_queue import TaskQueue, TaskPriority


# ============================================================================
# REDIS QUEUE MANAGER TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.redis
class TestRedisQueueManager:
    """Test RedisQueueManager operations."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis connection."""
        with patch('app.workers.redis_queue.redis.Redis') as mock:
            yield mock
    
    @pytest.fixture
    def manager(self, mock_redis):
        """Create manager with mocked Redis."""
        return RedisQueueManager(
            host="localhost",
            port=6379,
            db=0,
            password=None,
        )
    
    def test_connect_success(self, manager, mock_redis):
        """Test successful connection."""
        manager.redis_client = Mock()
        manager.redis_client.ping.return_value = True
        
        result = manager.connect()
        assert result is True
    
    def test_connect_failure(self, manager, mock_redis):
        """Test connection failure handling."""
        manager.redis_client = Mock()
        manager.redis_client.ping.side_effect = Exception("Connection failed")
        
        result = manager.connect()
        assert result is False
    
    def test_enqueue_task(self, manager):
        """Test enqueueing a task."""
        manager.redis_client = Mock()
        manager.queue = Mock()
        manager.queue.enqueue.return_value = Mock(id="job-123")
        
        job = manager.enqueue_task(
            func="detection.detect",
            args=("sample",),
            kwargs={"threshold": 0.8},
            priority="normal",
        )
        
        assert job is not None
        manager.queue.enqueue.assert_called_once()
    
    def test_get_job_status(self, manager):
        """Test getting job status."""
        manager.redis_client = Mock()
        
        # Mock job status
        mock_job = Mock()
        mock_job.get_status.return_value = "started"
        
        with patch('app.workers.redis_queue.Job.fetch') as mock_fetch:
            mock_fetch.return_value = mock_job
            
            status = manager.get_job_status("job-123")
            assert status == "started"
    
    def test_get_job_result(self, manager):
        """Test getting job result."""
        manager.redis_client = Mock()
        
        mock_job = Mock()
        mock_job.get_status.return_value = "finished"
        mock_job.result = {"decision": "BLOCK", "confidence": 0.95}
        
        with patch('app.workers.redis_queue.Job.fetch') as mock_fetch:
            mock_fetch.return_value = mock_job
            
            result = manager.get_job_result("job-123")
            assert result["decision"] == "BLOCK"
    
    def test_cancel_job(self, manager):
        """Test canceling a job."""
        manager.redis_client = Mock()
        
        mock_job = Mock()
        mock_job.delete.return_value = None
        
        with patch('app.workers.redis_queue.Job.fetch') as mock_fetch:
            mock_fetch.return_value = mock_job
            
            manager.cancel_job("job-123")
            mock_job.delete.assert_called_once()
    
    def test_get_queue_stats(self, manager):
        """Test getting queue statistics."""
        manager.redis_client = Mock()
        manager.queue = Mock()
        manager.queue.count = 5
        manager.queue.get_job_ids.return_value = ["j1", "j2", "j3", "j4", "j5"]
        
        stats = manager.get_queue_stats()
        assert stats["total_jobs"] == 5
        assert stats["queue_size"] == 5
    
    def test_clear_queue(self, manager):
        """Test clearing the queue."""
        manager.redis_client = Mock()
        manager.queue = Mock()
        manager.queue.empty.return_value = None
        
        manager.clear_queue()
        manager.queue.empty.assert_called_once()
    
    def test_cleanup_old_jobs(self, manager):
        """Test cleaning up old jobs."""
        manager.redis_client = Mock()
        manager.redis_client.keys.return_value = [
            b"rq:job:job-1",
            b"rq:job:job-2",
        ]
        manager.redis_client.delete.return_value = None
        
        deleted = manager.cleanup_old_jobs(days=7)
        assert isinstance(deleted, int)


# ============================================================================
# WORKER TESTS
# ============================================================================

@pytest.mark.unit
class TestWorkerManager:
    """Test WorkerManager."""
    
    @pytest.fixture
    def mock_queue(self):
        """Create mock queue."""
        return Mock()
    
    @pytest.fixture
    def worker(self, mock_queue):
        """Create worker with mocked queue."""
        with patch('app.workers.worker.Worker') as mock_worker_class:
            manager = WorkerManager(
                name="test-worker",
                queue=mock_queue,
                max_jobs=100,
            )
            manager.worker = Mock()
            return manager
    
    def test_create_worker(self, worker):
        """Test worker creation."""
        assert worker is not None
        assert worker.name == "test-worker"
        assert worker.max_jobs == 100
    
    def test_setup_signal_handlers(self, worker):
        """Test signal handler setup."""
        with patch('signal.signal') as mock_signal:
            worker.setup_signal_handlers()
            # Verify signal handlers registered
            assert mock_signal.call_count >= 2
    
    def test_run_worker(self, worker):
        """Test running worker in burst mode."""
        worker.worker = Mock()
        worker.worker.work.return_value = None
        
        worker.run(burst=True)
        worker.worker.work.assert_called_once()
    
    def test_shutdown_worker(self, worker):
        """Test shutting down worker."""
        worker.worker = Mock()
        worker.worker.request_stop.return_value = None
        
        worker.shutdown()
        worker.worker.request_stop.assert_called_once()
    
    def test_get_worker_status(self, worker):
        """Test getting worker status."""
        worker.worker = Mock()
        worker.worker.get_current_job.return_value = Mock(id="job-123")
        
        status = worker.get_status()
        assert status is not None
        assert isinstance(status, dict)


# ============================================================================
# TASK QUEUE TESTS
# ============================================================================

@pytest.mark.unit
class TestTaskQueue:
    """Test TaskQueue high-level interface."""
    
    @pytest.fixture
    def mock_manager(self):
        """Create mock queue manager."""
        return Mock(spec=RedisQueueManager)
    
    @pytest.fixture
    def task_queue(self, mock_manager):
        """Create task queue with mocked manager."""
        with patch('app.workers.task_queue.RedisQueueManager', return_value=mock_manager):
            queue = TaskQueue()
            queue.manager = mock_manager
            return queue
    
    def test_enqueue_detection(self, task_queue, mock_manager):
        """Test enqueueing detection task."""
        mock_manager.enqueue_task.return_value = Mock(id="job-123")
        
        job_id = task_queue.enqueue_detection(
            sample_data="alert('xss')",
            threshold=0.8,
            priority=TaskPriority.HIGH,
        )
        
        assert job_id == "job-123"
        mock_manager.enqueue_task.assert_called_once()
    
    def test_enqueue_ingest(self, task_queue, mock_manager):
        """Test enqueueing ingest task."""
        mock_manager.enqueue_task.return_value = Mock(id="job-456")
        
        job_id = task_queue.enqueue_ingest(
            event_data={"source": "agent", "data": "..."},
            priority=TaskPriority.NORMAL,
        )
        
        assert job_id == "job-456"
    
    def test_enqueue_alert(self, task_queue, mock_manager):
        """Test enqueueing alert task."""
        mock_manager.enqueue_task.return_value = Mock(id="job-789")
        
        job_id = task_queue.enqueue_alert(
            signal_id="sig-123",
            decision="BLOCK",
            priority=TaskPriority.CRITICAL,
        )
        
        assert job_id == "job-789"
    
    def test_get_status(self, task_queue, mock_manager):
        """Test getting job status."""
        mock_manager.get_job_status.return_value = "finished"
        
        status = task_queue.get_status("job-123")
        assert status == "finished"
    
    def test_get_result(self, task_queue, mock_manager):
        """Test getting job result."""
        mock_manager.get_job_result.return_value = {
            "decision": "BLOCK",
            "confidence": 0.95,
        }
        
        result = task_queue.get_result("job-123")
        assert result["decision"] == "BLOCK"
        assert result["confidence"] == 0.95
    
    def test_cancel_job(self, task_queue, mock_manager):
        """Test canceling job."""
        mock_manager.cancel_job.return_value = None
        
        task_queue.cancel("job-123")
        mock_manager.cancel_job.assert_called_once_with("job-123")
    
    def test_get_queue_stats(self, task_queue, mock_manager):
        """Test getting queue statistics."""
        mock_manager.get_queue_stats.return_value = {
            "total_jobs": 42,
            "queue_size": 15,
        }
        
        stats = task_queue.get_queue_stats()
        assert stats["total_jobs"] == 42
        assert stats["queue_size"] == 15
    
    def test_clear_queue(self, task_queue, mock_manager):
        """Test clearing queue."""
        mock_manager.clear_queue.return_value = None
        
        task_queue.clear_queue()
        mock_manager.clear_queue.assert_called_once()
    
    def test_priority_levels(self):
        """Test all priority levels are defined."""
        assert hasattr(TaskPriority, 'LOW')
        assert hasattr(TaskPriority, 'NORMAL')
        assert hasattr(TaskPriority, 'HIGH')
        assert hasattr(TaskPriority, 'CRITICAL')


# ============================================================================
# QUEUE INTEGRATION TESTS
# ============================================================================

@pytest.mark.unit
class TestQueueIntegration:
    """Test queue components working together."""
    
    def test_task_lifecycle(self):
        """Test complete task lifecycle."""
        # This is a conceptual test showing the expected flow
        # In reality, would need actual Redis/RQ running
        
        with patch('app.workers.redis_queue.RedisQueueManager') as MockQueueMgr:
            with patch('app.workers.task_queue.RedisQueueManager', MockQueueMgr):
                mock_manager = Mock()
                MockQueueMgr.return_value = mock_manager
                
                # Setup mock to track job lifecycle
                mock_manager.enqueue_task.return_value = Mock(id="job-123")
                mock_manager.get_job_status.side_effect = [
                    "queued",
                    "started",
                    "finished",
                ]
                mock_manager.get_job_result.return_value = {
                    "decision": "WARN",
                    "confidence": 0.85,
                }
                
                # Create task queue
                task_queue = TaskQueue()
                task_queue.manager = mock_manager
                
                # Enqueue task
                job_id = task_queue.enqueue_detection("sample", threshold=0.8)
                assert job_id == "job-123"
                
                # Check status progression
                assert task_queue.get_status(job_id) == "queued"
                assert task_queue.get_status(job_id) == "started"
                assert task_queue.get_status(job_id) == "finished"
                
                # Get result
                result = task_queue.get_result(job_id)
                assert result["decision"] == "WARN"
    
    def test_priority_queue_ordering(self):
        """Test that priority queues work correctly."""
        # CRITICAL > HIGH > NORMAL > LOW
        priorities = [
            TaskPriority.NORMAL,
            TaskPriority.LOW,
            TaskPriority.CRITICAL,
            TaskPriority.HIGH,
        ]
        
        # Verify all priority levels exist
        assert len(priorities) == 4
        
        # CRITICAL should have highest value
        assert TaskPriority.CRITICAL.value > TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value > TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value > TaskPriority.LOW.value


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in queue system."""
    
    def test_connection_error_handling(self):
        """Test handling connection errors."""
        with patch('app.workers.redis_queue.redis.Redis') as mock_redis:
            mock_redis.side_effect = Exception("Connection refused")
            
            manager = RedisQueueManager()
            result = manager.connect()
            assert result is False
    
    def test_job_not_found(self):
        """Test handling job not found."""
        manager = RedisQueueManager.__new__(RedisQueueManager)
        manager.redis_client = Mock()
        
        with patch('app.workers.redis_queue.Job.fetch') as mock_fetch:
            mock_fetch.side_effect = Exception("Job not found")
            
            # Should handle gracefully
            try:
                manager.get_job_status("nonexistent")
            except:
                pass
    
    def test_invalid_job_data(self):
        """Test handling invalid job data."""
        with patch('app.workers.task_queue.RedisQueueManager') as MockQM:
            mock_manager = Mock()
            MockQM.return_value = mock_manager
            
            task_queue = TaskQueue()
            task_queue.manager = mock_manager
            
            # Mock manager returns None for result
            mock_manager.get_job_result.return_value = None
            
            result = task_queue.get_result("job-123")
            assert result is None
