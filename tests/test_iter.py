"""Tests for _iter module."""

from filestag._iter import limit_iter, batch_iter


class TestLimitIter:
    """Tests for limit_iter function."""

    def test_limit_iter_basic(self):
        """Test basic limiting functionality."""
        result = list(limit_iter(iter(range(10)), 5))
        assert result == [0, 1, 2, 3, 4]

    def test_limit_iter_unlimited(self):
        """Test with unlimited count (-1)."""
        result = list(limit_iter(iter(range(5)), -1))
        assert result == [0, 1, 2, 3, 4]

    def test_limit_iter_zero(self):
        """Test with zero count."""
        result = list(limit_iter(iter(range(10)), 0))
        assert result == []

    def test_limit_iter_exceeds_source(self):
        """Test when limit exceeds source length."""
        result = list(limit_iter(iter(range(3)), 10))
        assert result == [0, 1, 2]

    def test_limit_iter_empty(self):
        """Test with empty iterator."""
        result = list(limit_iter(iter([]), 5))
        assert result == []

    def test_limit_iter_one(self):
        """Test with limit of 1."""
        result = list(limit_iter(iter(range(10)), 1))
        assert result == [0]


class TestBatchIter:
    """Tests for batch_iter function."""

    def test_batch_iter_basic(self):
        """Test basic batching functionality."""
        result = list(batch_iter(iter(range(10)), 3))
        assert result == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]

    def test_batch_iter_exact_division(self):
        """Test when elements divide evenly into batches."""
        result = list(batch_iter(iter(range(9)), 3))
        assert result == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]

    def test_batch_iter_single_batch(self):
        """Test when all elements fit in one batch."""
        result = list(batch_iter(iter(range(3)), 10))
        assert result == [[0, 1, 2]]

    def test_batch_iter_empty(self):
        """Test with empty iterator."""
        result = list(batch_iter(iter([]), 3))
        assert result == []

    def test_batch_iter_single_element_batches(self):
        """Test with batch size of 1."""
        result = list(batch_iter(iter(range(3)), 1))
        assert result == [[0], [1], [2]]

    def test_batch_iter_fast_mode(self):
        """Test fast mode (converts to list first)."""
        result = list(batch_iter(iter(range(10)), 3, fast=True))
        assert result == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]

    def test_batch_iter_with_list(self):
        """Test with list input (should use fast path)."""
        result = list(batch_iter([0, 1, 2, 3, 4], 2))
        assert result == [[0, 1], [2, 3], [4]]

    def test_batch_iter_strings(self):
        """Test batching with strings."""
        result = list(batch_iter(iter(["a", "b", "c", "d"]), 2))
        assert result == [["a", "b"], ["c", "d"]]
