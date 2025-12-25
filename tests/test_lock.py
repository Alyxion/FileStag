"""Tests for _lock module."""

import threading
import time

from filestag._lock import StagLock


class TestStagLock:
    """Tests for StagLock class."""

    def test_basic_lock(self):
        """Test basic lock functionality."""
        lock = StagLock()
        lock.acquire()
        lock.release()

    def test_context_manager(self):
        """Test context manager usage."""
        lock = StagLock()
        with lock as acquired_lock:
            assert acquired_lock is lock

    def test_reentrant_lock(self):
        """Test that lock is reentrant (same thread can acquire multiple times)."""
        lock = StagLock()
        with lock:
            with lock:
                pass  # Should not deadlock

    def test_no_thread_lock(self):
        """Test lock with thread_lock=False."""
        lock = StagLock(thread_lock=False)
        assert lock.thread_lock is None

        # Should not raise even without actual locking
        lock.acquire()
        lock.release()

        with lock:
            pass

    def test_thread_safety(self):
        """Test that lock provides thread safety."""
        lock = StagLock()
        counter = [0]
        errors = []

        def increment():
            for _ in range(100):
                with lock:
                    current = counter[0]
                    time.sleep(0.0001)  # Small delay to increase chance of race condition
                    counter[0] = current + 1

        threads = [threading.Thread(target=increment) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # With proper locking, counter should be exactly 500
        assert counter[0] == 500

    def test_exit_with_exception(self):
        """Test that lock is released even when exception occurs."""
        lock = StagLock()

        try:
            with lock:
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Lock should be released, so we can acquire it again
        lock.acquire()
        lock.release()
