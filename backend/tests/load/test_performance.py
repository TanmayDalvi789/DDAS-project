"""
Phase 4: Load and Performance Tests
Tests for high-concurrency and performance scenarios.
"""

import pytest
from unittest.mock import Mock, patch
import time
from concurrent.futures import ThreadPoolExecutor
import threading


# ============================================================================
# QUEUE THROUGHPUT TESTS
# ============================================================================

@pytest.mark.slow
@pytest.mark.load
class TestQueueThroughput:
    """Test queue system throughput and performance."""
    
    def test_enqueue_100_tasks(self):
        """Test enqueueing 100 tasks."""
        with patch('app.workers.task_queue.RedisQueueManager') as MockQM:
            mock_manager = Mock()
            MockQM.return_value = mock_manager
            
            from app.workers.task_queue import TaskQueue, TaskPriority
            
            # Mock to track calls
            job_counter = {"count": 0}
            
            def mock_enqueue(*args, **kwargs):
                job_counter["count"] += 1
                return Mock(id=f"job-{job_counter['count']}")
            
            mock_manager.enqueue_task.side_effect = mock_enqueue
            
            task_queue = TaskQueue()
            task_queue.manager = mock_manager
            
            # Enqueue 100 tasks
            start_time = time.time()
            for i in range(100):
                task_queue.enqueue_detection(
                    sample_data=f"sample-{i}",
                    threshold=0.8,
                    priority=TaskPriority.NORMAL,
                )
            elapsed = time.time() - start_time
            
            assert job_counter["count"] == 100
            # Should complete reasonably fast (< 5 seconds)
            assert elapsed < 5.0
    
    def test_enqueue_1000_tasks(self):
        """Test enqueueing 1000 tasks."""
        with patch('app.workers.task_queue.RedisQueueManager') as MockQM:
            mock_manager = Mock()
            MockQM.return_value = mock_manager
            
            from app.workers.task_queue import TaskQueue, TaskPriority
            
            job_counter = {"count": 0}
            
            def mock_enqueue(*args, **kwargs):
                job_counter["count"] += 1
                return Mock(id=f"job-{job_counter['count']}")
            
            mock_manager.enqueue_task.side_effect = mock_enqueue
            
            task_queue = TaskQueue()
            task_queue.manager = mock_manager
            
            # Enqueue 1000 tasks
            start_time = time.time()
            for i in range(1000):
                task_queue.enqueue_detection(
                    sample_data=f"sample-{i}",
                    threshold=0.8,
                    priority=TaskPriority.NORMAL,
                )
            elapsed = time.time() - start_time
            
            assert job_counter["count"] == 1000
            # Should complete in reasonable time (< 30 seconds)
            assert elapsed < 30.0
    
    def test_mixed_priority_throughput(self):
        """Test throughput with mixed priority tasks."""
        with patch('app.workers.task_queue.RedisQueueManager') as MockQM:
            mock_manager = Mock()
            MockQM.return_value = mock_manager
            
            from app.workers.task_queue import TaskQueue, TaskPriority
            
            priorities = [
                TaskPriority.LOW,
                TaskPriority.NORMAL,
                TaskPriority.HIGH,
                TaskPriority.CRITICAL,
            ]
            
            job_counter = {"count": 0}
            
            def mock_enqueue(*args, **kwargs):
                job_counter["count"] += 1
                return Mock(id=f"job-{job_counter['count']}")
            
            mock_manager.enqueue_task.side_effect = mock_enqueue
            
            task_queue = TaskQueue()
            task_queue.manager = mock_manager
            
            # Enqueue 250 tasks per priority (1000 total)
            start_time = time.time()
            for priority in priorities:
                for i in range(250):
                    task_queue.enqueue_detection(
                        sample_data=f"sample-{i}",
                        threshold=0.8,
                        priority=priority,
                    )
            elapsed = time.time() - start_time
            
            assert job_counter["count"] == 1000
            assert elapsed < 30.0


# ============================================================================
# DATABASE CONCURRENT ACCESS TESTS
# ============================================================================

@pytest.mark.slow
@pytest.mark.load
@pytest.mark.db
class TestDatabaseConcurrency:
    """Test database concurrent access patterns."""
    
    def test_concurrent_event_insertion(self, test_db_session):
        """Test concurrent event insertion."""
        from app.db.repositories.events_repo import EventsRepository
        
        repo = EventsRepository(test_db_session)
        
        # Simulate 50 concurrent insertions
        errors = []
        results = []
        lock = threading.Lock()
        
        def insert_event(index):
            try:
                event = repo.create(
                    source_id=f"agent-{index}",
                    source_type="agent",
                    event_type="scan",
                    payload={"index": index},
                )
                with lock:
                    results.append(event)
            except Exception as e:
                with lock:
                    errors.append(str(e))
        
        # Run concurrent inserts
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(insert_event, i) for i in range(50)]
            for future in futures:
                future.result()
        
        # Verify success
        assert len(errors) == 0
        assert len(results) == 50
    
    def test_concurrent_read_write(self, test_db_session):
        """Test concurrent read/write operations."""
        from app.db.repositories.events_repo import EventsRepository
        from app.db.repositories.signals_repo import SignalsRepository
        
        events_repo = EventsRepository(test_db_session)
        signals_repo = SignalsRepository(test_db_session)
        
        # Create test event
        event = events_repo.create("src-001", "agent", "scan", {})
        
        results = {"reads": 0, "writes": 0}
        errors = []
        lock = threading.Lock()
        
        def read_event(index):
            try:
                retrieved = events_repo.get_by_id(event.id)
                if retrieved:
                    with lock:
                        results["reads"] += 1
            except Exception as e:
                with lock:
                    errors.append(str(e))
        
        def write_signal(index):
            try:
                signal = signals_repo.create(
                    event_id=event.id,
                    detection_type=f"type-{index}",
                    confidence=0.8,
                    detected_items=[],
                    raw_result={},
                )
                with lock:
                    results["writes"] += 1
            except Exception as e:
                with lock:
                    errors.append(str(e))
        
        # Mix reads and writes
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(50):
                if i % 2 == 0:
                    futures.append(executor.submit(read_event, i))
                else:
                    futures.append(executor.submit(write_signal, i))
            for future in futures:
                future.result()
        
        assert len(errors) == 0
        assert results["reads"] == 25
        assert results["writes"] == 25


# ============================================================================
# DETECTION ALGORITHM PERFORMANCE TESTS
# ============================================================================

@pytest.mark.slow
@pytest.mark.load
class TestDetectionPerformance:
    """Test detection algorithm performance."""
    
    def test_fuzzy_detection_performance(self):
        """Test fuzzy detection performance on large strings."""
        from detection.fuzzy_detection import FuzzyDetection
        
        detector = FuzzyDetection()
        
        # Create test data
        reference = "a" * 10000  # 10KB string
        sample = "a" * 9990 + "b" * 10  # 99% match
        
        # Measure detection time
        start_time = time.time()
        result = detector.detect(reference, sample)
        elapsed = time.time() - start_time
        
        # Should complete reasonably fast (< 1 second)
        assert elapsed < 1.0
        assert result.confidence > 0.90
    
    def test_batch_detection_performance(self):
        """Test batch detection performance."""
        from detection.fuzzy_detection import FuzzyDetection
        
        detector = FuzzyDetection()
        
        reference = "alert(window,'xss')"
        samples = [
            f"alert(window,'xss-variant-{i}')" 
            for i in range(100)
        ]
        
        # Measure batch detection time
        start_time = time.time()
        results = detector.batch_detect(reference, samples)
        elapsed = time.time() - start_time
        
        assert len(results) == 100
        # Batch should be faster than sequential for 100 samples
        assert elapsed < 10.0


# ============================================================================
# STRESS TESTS
# ============================================================================

@pytest.mark.slow
@pytest.mark.load
class TestStressScenarios:
    """Test system behavior under stress."""
    
    def test_high_event_volume(self, test_db_session):
        """Test handling high volume of events."""
        from app.db.repositories.events_repo import EventsRepository
        
        repo = EventsRepository(test_db_session)
        
        start_time = time.time()
        
        # Create 1000 events
        for i in range(1000):
            repo.create(
                source_id=f"source-{i % 10}",
                source_type="agent",
                event_type="scan",
                payload={"sequence": i},
            )
        
        elapsed = time.time() - start_time
        
        # Should handle 1000 events reasonably
        assert elapsed < 60.0  # Less than 1 minute
    
    def test_task_queue_under_load(self):
        """Test queue system under high load."""
        with patch('app.workers.task_queue.RedisQueueManager') as MockQM:
            mock_manager = Mock()
            MockQM.return_value = mock_manager
            
            from app.workers.task_queue import TaskQueue, TaskPriority
            
            job_counter = {"count": 0}
            
            def mock_enqueue(*args, **kwargs):
                job_counter["count"] += 1
                return Mock(id=f"job-{job_counter['count']}")
            
            mock_manager.enqueue_task.side_effect = mock_enqueue
            mock_manager.get_queue_stats.return_value = {
                "total_jobs": job_counter.get("count", 0),
                "queue_size": job_counter.get("count", 0),
            }
            
            task_queue = TaskQueue()
            task_queue.manager = mock_manager
            
            start_time = time.time()
            
            # Enqueue 5000 tasks rapidly
            for i in range(5000):
                task_queue.enqueue_detection(
                    sample_data=f"sample-{i}",
                    threshold=0.8,
                    priority=TaskPriority.NORMAL if i % 4 == 0 else TaskPriority.NORMAL,
                )
            
            elapsed = time.time() - start_time
            
            assert job_counter["count"] == 5000
            # 5000 tasks should enqueue in reasonable time
            assert elapsed < 120.0


# ============================================================================
# MEMORY AND RESOURCE TESTS
# ============================================================================

@pytest.mark.slow
@pytest.mark.load
class TestResourceUsage:
    """Test memory and resource usage patterns."""
    
    def test_large_payload_handling(self, test_db_session):
        """Test handling large event payloads."""
        from app.db.repositories.events_repo import EventsRepository
        
        repo = EventsRepository(test_db_session)
        
        # Create event with large payload (1MB)
        large_payload = {"data": "x" * (1024 * 1024)}
        
        event = repo.create(
            source_id="src-001",
            source_type="agent",
            event_type="scan",
            payload=large_payload,
        )
        
        assert event is not None
        
        # Retrieve and verify
        retrieved = repo.get_by_id(event.id)
        assert retrieved is not None
        assert len(retrieved.payload["data"]) == (1024 * 1024)
    
    def test_large_result_set(self, test_db_session):
        """Test querying large result sets."""
        from app.db.repositories.events_repo import EventsRepository
        
        repo = EventsRepository(test_db_session)
        
        # Create 1000 events
        for i in range(1000):
            repo.create(
                source_id="src-001",
                source_type="agent",
                event_type="scan",
                payload={"index": i},
            )
        
        # Query all events
        start_time = time.time()
        events = repo.list_recent(limit=1000)
        elapsed = time.time() - start_time
        
        assert len(events) == 1000
        # Large query should complete reasonably fast
        assert elapsed < 5.0


# ============================================================================
# SCALABILITY TESTS
# ============================================================================

@pytest.mark.slow
@pytest.mark.load
class TestScalability:
    """Test system scalability characteristics."""
    
    def test_linear_scaling_event_creation(self, test_db_session):
        """Test that event creation scales linearly."""
        from app.db.repositories.events_repo import EventsRepository
        
        repo = EventsRepository(test_db_session)
        times = {}
        
        for size in [100, 200, 400]:
            start_time = time.time()
            for i in range(size):
                repo.create(
                    source_id=f"src-{i}",
                    source_type="agent",
                    event_type="scan",
                    payload={},
                )
            elapsed = time.time() - start_time
            times[size] = elapsed
        
        # Verify approximate linear scaling
        # 200 events should take roughly 2x of 100
        # 400 events should take roughly 2x of 200
        ratio_200_100 = times[200] / times[100]
        ratio_400_200 = times[400] / times[200]
        
        # Allow 50% variance from linear
        assert 1.5 < ratio_200_100 < 2.5
        assert 1.5 < ratio_400_200 < 2.5
