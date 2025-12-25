"""Tests for cache module."""

import os
import shutil
from pathlib import Path

import pytest

from filestag.cache import Cache, CacheRef, DiskCache, get_global_cache
from filestag.cache._bundle import bundle, unbundle, _serialize_value, _deserialize_value


class TestBundle:
    """Tests for bundle/unbundle functions."""

    def test_bundle_dict(self):
        """Test bundling a dictionary."""
        data = {"key": "value", "num": 42}
        bundled = bundle(data)
        assert isinstance(bundled, bytes)

        unbundled = unbundle(bundled)
        assert unbundled == data

    def test_bundle_nested(self):
        """Test bundling nested structures."""
        data = {"outer": {"inner": {"deep": "value"}}}
        bundled = bundle(data)
        unbundled = unbundle(bundled)
        assert unbundled == data

    def test_bundle_bytes(self):
        """Test bundling with bytes values."""
        data = {"binary": b"hello bytes"}
        bundled = bundle(data)
        unbundled = unbundle(bundled)
        assert unbundled["binary"] == b"hello bytes"

    def test_bundle_list(self):
        """Test bundling lists."""
        data = {"items": [1, 2, 3, "four"]}
        bundled = bundle(data)
        unbundled = unbundle(bundled)
        assert unbundled == data

    def test_bundle_tuple(self):
        """Test bundling tuples."""
        data = {"coords": (1, 2, 3)}
        bundled = bundle(data)
        unbundled = unbundle(bundled)
        assert unbundled["coords"] == (1, 2, 3)

    def test_bundle_set(self):
        """Test bundling sets."""
        data = {"unique": {1, 2, 3}}
        bundled = bundle(data)
        unbundled = unbundle(bundled)
        assert unbundled["unique"] == {1, 2, 3}

    def test_bundle_mixed(self):
        """Test bundling mixed types."""
        data = {
            "string": "hello",
            "number": 123,
            "float": 3.14,
            "bool": True,
            "none": None,
            "bytes": b"binary",
            "list": [1, 2, 3],
            "tuple": (4, 5, 6),
            "set": {7, 8, 9},
        }
        bundled = bundle(data)
        unbundled = unbundle(bundled)

        assert unbundled["string"] == "hello"
        assert unbundled["number"] == 123
        assert unbundled["bytes"] == b"binary"
        assert unbundled["tuple"] == (4, 5, 6)
        assert unbundled["set"] == {7, 8, 9}

    def test_invalid_bundle_version(self):
        """Test unbundling with invalid version."""
        import json

        invalid_data = json.dumps({"version": 999, "data": {}}).encode("utf-8")
        with pytest.raises(ValueError):
            unbundle(invalid_data)


class TestDiskCache:
    """Tests for DiskCache class."""

    def test_set_and_get(self, temp_dir):
        """Test setting and getting values."""
        cache = DiskCache(cache_dir=temp_dir)
        cache.set("key1", "value1")

        result = cache.get("key1")
        assert result == "value1"

    def test_get_nonexistent(self, temp_dir):
        """Test getting non-existent key returns default."""
        cache = DiskCache(cache_dir=temp_dir)
        result = cache.get("nonexistent", default="default_value")
        assert result == "default_value"

    def test_versioning(self, temp_dir):
        """Test version-based cache invalidation."""
        cache = DiskCache(version="1", cache_dir=temp_dir)
        cache.set("versioned", "v1_data")

        # Same version should work
        result = cache.get("versioned")
        assert result == "v1_data"

        # Different version should not find it
        cache2 = DiskCache(version="2", cache_dir=temp_dir)
        result = cache2.get("versioned")
        assert result is None

    def test_delete(self, temp_dir):
        """Test deleting a cache entry."""
        cache = DiskCache(cache_dir=temp_dir)
        cache.set("to_delete", "data")

        result = cache.delete("to_delete")
        assert result is True

        result = cache.get("to_delete")
        assert result is None

    def test_delete_nonexistent(self, temp_dir):
        """Test deleting non-existent entry."""
        cache = DiskCache(cache_dir=temp_dir)
        result = cache.delete("nonexistent")
        assert result is False

    def test_clear(self, temp_dir):
        """Test clearing the cache."""
        cache = DiskCache(cache_dir=temp_dir)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_contains(self, temp_dir):
        """Test __contains__ method."""
        cache = DiskCache(cache_dir=temp_dir)
        cache.set("exists", "value")

        assert "exists" in cache
        assert "not_exists" not in cache

    def test_encode_name(self):
        """Test name encoding is consistent."""
        name1 = DiskCache.encode_name("test_key")
        name2 = DiskCache.encode_name("test_key")
        name3 = DiskCache.encode_name("different_key")

        assert name1 == name2
        assert name1 != name3

    def test_version_property(self, temp_dir):
        """Test version property."""
        cache = DiskCache(version=123, cache_dir=temp_dir)
        assert cache.version == "123"


class TestCache:
    """Tests for Cache class."""

    def test_set_and_get(self):
        """Test setting and getting values."""
        cache = Cache()
        cache.set("key1", "value1")

        result = cache.get("key1")
        assert result == "value1"

    def test_get_default(self):
        """Test getting with default value."""
        cache = Cache()
        result = cache.get("nonexistent", default="default")
        assert result == "default"

    def test_contains(self):
        """Test __contains__ method."""
        cache = Cache()
        cache.set("exists", "value")

        assert "exists" in cache
        assert "not_exists" not in cache

    def test_versioning(self):
        """Test entry-level versioning."""
        cache = Cache()
        cache.set("versioned", "data", version=1)

        assert cache.get("versioned", version=1) == "data"
        assert cache.get("versioned", version=2) is None

    def test_key_with_version(self):
        """Test key@version syntax."""
        cache = Cache()
        cache.set("mykey@1", "version1_data")

        result = cache.get("mykey@1")
        assert result == "version1_data"

    def test_remove(self):
        """Test removing entries."""
        cache = Cache()
        cache.set("to_delete", "data")

        result = cache.remove("to_delete")
        assert result == 1
        assert "to_delete" not in cache

    def test_lpush(self):
        """Test list push operation."""
        cache = Cache()
        cache.lpush("mylist", "item1")
        cache.lpush("mylist", "item2")

        result = cache.get("mylist")
        assert isinstance(result, list)
        assert "item1" in result
        assert "item2" in result

    def test_pop(self):
        """Test pop operation."""
        cache = Cache()
        cache.lpush("poplist", "first")
        cache.lpush("poplist", "second")

        result = cache.pop("poplist", index=0)
        assert result == "first"

        # List should now only have one item
        remaining = cache.get("poplist")
        assert len(remaining) == 1

    def test_pop_from_end(self):
        """Test pop from end of list."""
        cache = Cache()
        cache.lpush("endpop", "first")
        cache.lpush("endpop", "second")

        result = cache.pop("endpop", index=-1)
        assert result == "second"

    def test_pop_empty(self):
        """Test pop from empty or non-existent key."""
        cache = Cache()
        result = cache.pop("nonexistent", default="default")
        assert result == "default"

    def test_pop_single_value(self):
        """Test pop from single value (not list)."""
        cache = Cache()
        cache.set("single", "value")

        result = cache.pop("single")
        assert result == "value"
        assert "single" not in cache

    def test_clear(self):
        """Test clearing the cache."""
        cache = Cache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert "key1" not in cache
        assert "key2" not in cache

    def test_disk_prefix(self, temp_dir):
        """Test disk storage with $ prefix."""
        cache = Cache(cache_dir=temp_dir)
        cache.set("$disk_key", "disk_value")

        # Should be stored on disk
        result = cache.get("$disk_key")
        assert result == "disk_value"

    def test_create_ref(self):
        """Test creating a cache reference."""
        cache = Cache()
        ref = cache.create_ref("ref_key")

        assert isinstance(ref, CacheRef)
        assert ref.name == "ref_key"

    def test_async_fetch(self):
        """Test processing async updates."""
        cache = Cache()
        cache.set_async("async_key", "async_value")

        # Process pending updates
        cache.async_fetch()

        result = cache.get("async_key")
        assert result == "async_value"

    def test_lpush_async(self):
        """Test async list push."""
        cache = Cache()
        cache.lpush_async("async_list", "item1")
        cache.lpush_async("async_list", "item2")

        cache.async_fetch()

        result = cache.get("async_list")
        assert "item1" in result
        assert "item2" in result

    def test_thread_safety(self):
        """Test thread-safe operations."""
        import threading

        cache = Cache()
        results = []

        def worker(i):
            cache.set(f"thread_{i}", f"value_{i}")
            results.append(cache.get(f"thread_{i}"))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10


class TestCacheRef:
    """Tests for CacheRef class."""

    def test_set(self):
        """Test setting value through reference."""
        cache = Cache()
        ref = CacheRef(cache, "ref_key")

        ref.set("ref_value")
        assert cache.get("ref_key") == "ref_value"

    def test_push(self):
        """Test pushing value through reference."""
        cache = Cache()
        ref = CacheRef(cache, "ref_list")

        ref.push("item1")
        ref.push("item2")

        result = cache.get("ref_list")
        assert "item1" in result
        assert "item2" in result

    def test_pop(self):
        """Test popping value through reference."""
        cache = Cache()
        cache.lpush("pop_ref", "first")
        cache.lpush("pop_ref", "second")

        ref = CacheRef(cache, "pop_ref")
        result = ref.pop()

        assert result == "first"

    def test_async_operations(self):
        """Test async operations through reference."""
        cache = Cache()
        ref = CacheRef(cache, "async_ref", update_async=True)

        ref.set("async_value")
        cache.async_fetch()

        assert cache.get("async_ref") == "async_value"

    def test_async_push(self):
        """Test async push through reference."""
        cache = Cache()
        ref = CacheRef(cache, "async_push_ref", update_async=True)

        ref.push("async_item")
        cache.async_fetch()

        result = cache.get("async_push_ref")
        assert "async_item" in result


class TestGetGlobalCache:
    """Tests for get_global_cache function."""

    def test_returns_cache(self):
        """Test that get_global_cache returns a Cache instance."""
        cache = get_global_cache()
        assert isinstance(cache, Cache)

    def test_returns_same_instance(self):
        """Test that get_global_cache returns the same instance."""
        cache1 = get_global_cache()
        cache2 = get_global_cache()
        assert cache1 is cache2

    def test_usable(self):
        """Test that the global cache is usable."""
        cache = get_global_cache()
        cache.set("global_test", "value")
        assert cache.get("global_test") == "value"
        cache.remove("global_test")


class TestCacheAdvanced:
    """Advanced tests for Cache class."""

    def test_cache_method_basic(self):
        """Test cache() method with generator."""
        cache = Cache()
        call_count = 0

        def generator():
            nonlocal call_count
            call_count += 1
            return "generated_value"

        # First call should generate
        result1 = cache.cache("cached_key", generator)
        assert result1 == "generated_value"
        assert call_count == 1

        # Second call should use cache
        result2 = cache.cache("cached_key", generator)
        assert result2 == "generated_value"
        assert call_count == 1  # Generator not called again

    def test_cache_method_with_version(self):
        """Test cache() method with version parameter."""
        cache = Cache()

        def generator(val):
            return f"value_{val}"

        result1 = cache.cache("versioned_cache", generator, "a", version=1)
        assert result1 == "value_a"

        # Different version should regenerate
        result2 = cache.cache("versioned_cache", generator, "b", version=2)
        assert result2 == "value_b"

    def test_cache_method_with_hash_val(self):
        """Test cache() method with hash_val parameter."""
        cache = Cache()

        def generator():
            return "computed"

        result1 = cache.cache("hashed_cache", generator, hash_val="hash1")
        assert result1 == "computed"

        # Same hash should use cache
        result2 = cache.cache("hashed_cache", generator, hash_val="hash1")
        assert result2 == "computed"

    def test_get_app_session_id(self):
        """Test get_app_session_id class method."""
        session_id = Cache.get_app_session_id()
        assert isinstance(session_id, int)

    def test_override_app_session_id(self):
        """Test override_app_session_id class method."""
        original_id = Cache.get_app_session_id()

        Cache.override_app_session_id(99999)
        assert Cache.get_app_session_id() == 99999

        # Restore original
        Cache.override_app_session_id(original_id)

    def test_get_key_and_version_basic(self):
        """Test get_key_and_version with basic inputs."""
        key, version = Cache.get_key_and_version("mykey", "1", "2")
        assert key == "mykey"
        assert "1" in version

    def test_get_key_and_version_with_at_syntax(self):
        """Test get_key_and_version with @ syntax in key."""
        key, version = Cache.get_key_and_version("mykey@5", "1", "2")
        assert key == "mykey"
        assert "5" in version

    def test_get_key_and_version_minor_zero(self):
        """Test get_key_and_version with minor=0."""
        key, version = Cache.get_key_and_version("mykey", "1", 0)
        assert key == "mykey"
        session_id = str(Cache.get_app_session_id())
        assert session_id in version

    def test_get_key_and_version_negative_minor(self):
        """Test get_key_and_version with negative minor."""
        key, version = Cache.get_key_and_version("mykey", "1", "-custom")
        assert key == "mykey"
        assert version == "-custom"

    def test_version_property(self):
        """Test version property."""
        cache = Cache(version="test_v1")
        assert cache.version == "test_v1"

    def test_set_with_keep(self):
        """Test set with keep=True."""
        cache = Cache()
        cache.set("keep_key", "value", keep=True)
        assert cache.get("keep_key") == "value"

    def test_inc(self):
        """Test increment operation."""
        cache = Cache()
        cache.set("counter", 0)

        result = cache.inc("counter")
        assert result == 1
        assert cache.get("counter") == 1

    def test_inc_nonexistent(self):
        """Test increment on non-existent key."""
        cache = Cache()
        result = cache.inc("new_counter")
        assert result == 1

    def test_inc_with_amount(self):
        """Test increment with custom amount."""
        cache = Cache()
        cache.set("counter2", 10)

        result = cache.inc("counter2", value=5)
        assert result == 15

    def test_dec(self):
        """Test decrement operation."""
        cache = Cache()
        cache.set("dec_counter", 10)

        result = cache.dec("dec_counter", value=1)
        assert result == 9

    def test_get_with_version(self):
        """Test get with version mismatch."""
        cache = Cache()
        cache.set("ver_key", "ver_value", version=1)

        # Matching version
        assert cache.get("ver_key", version=1) == "ver_value"

        # Non-matching version
        assert cache.get("ver_key", version=2) is None

    def test_pop_empty_list(self):
        """Test pop from empty list."""
        cache = Cache()
        cache.set("empty_list", [])

        result = cache.pop("empty_list", default="default")
        assert result == "default"

    def test_remove_nonexistent(self):
        """Test remove on non-existent key."""
        cache = Cache()
        result = cache.remove("nonexistent_key")
        assert result == 0

    def test_remove_multiple_keys(self):
        """Test remove with list of keys."""
        cache = Cache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        result = cache.remove(["key1", "key2"])
        assert result == 2
        assert "key1" not in cache
        assert "key2" not in cache
        assert "key3" in cache

    def test_increase_revision(self):
        """Test increase_revision method."""
        cache = Cache()
        cache.set("rev_test", "value")

        rev1 = cache.increase_revision("rev_test")
        rev2 = cache.increase_revision("rev_test")

        assert rev2 > rev1

    def test_disk_key_prefix(self, temp_dir):
        """Test disk key with $ prefix persistence."""
        cache = Cache(cache_dir=temp_dir)
        cache.set("$persistent_key", {"data": "value"})

        result = cache.get("$persistent_key")
        assert result == {"data": "value"}

    def test_disk_key_inc(self, temp_dir):
        """Test disk key increment."""
        cache = Cache(cache_dir=temp_dir)
        cache.set("$disk_counter", 5)

        result = cache.inc("$disk_counter")
        assert result == 6

    def test_revision_tracking(self):
        """Test key revision tracking."""
        cache = Cache()
        cache.set("rev_key", "v1")
        rev1 = cache.get_revision("rev_key")

        cache.set("rev_key", "v2")
        rev2 = cache.get_revision("rev_key")

        assert rev2 > rev1

    def test_get_revision_nonexistent(self):
        """Test get_revision for non-existent key."""
        cache = Cache()
        rev = cache.get_revision("nonexistent")
        assert rev == 0

    def test_setitem_getitem(self):
        """Test __setitem__ and __getitem__."""
        cache = Cache()
        cache["key"] = "value"
        assert cache["key"] == "value"

    def test_getitem_keyerror(self):
        """Test __getitem__ raises KeyError for missing key."""
        cache = Cache()
        with pytest.raises(KeyError):
            _ = cache["nonexistent"]

    def test_load_unload(self):
        """Test load/unload lifecycle."""
        cache = Cache()
        # Default loaded is False
        assert cache.loaded == False

        cache.load()
        assert cache.loaded == True
        # Note: _is_loading stays True after load() completes

        cache.unload()
        assert cache.loaded == False

    def test_load_twice_raises(self):
        """Test loading twice raises RuntimeError."""
        cache = Cache()
        cache.load()

        with pytest.raises(RuntimeError):
            cache.load()

        # Clean up
        cache.unload()

    def test_unload_without_load_raises(self):
        """Test unloading without loading raises RuntimeError."""
        cache = Cache()

        with pytest.raises(RuntimeError):
            cache.unload()

    def test_add_volatile_member(self):
        """Test add_volatile_member."""
        cache = Cache()
        cache.add_volatile_member("test_member")

        # Should be in volatile cache entries
        assert ".test_member" in cache._volatile_cache_entries

    def test_disk_get_set_with_version(self, temp_dir):
        """Test disk cache with version in key."""
        cache = Cache(cache_dir=temp_dir)
        cache.set("$ver_key@1", "version1_value")

        result = cache.get("$ver_key@1")
        assert result == "version1_value"

    def test_lpush_multiple_values(self):
        """Test lpush with multiple values."""
        cache = Cache()
        cache.lpush("multi_list", "item1", "item2", "item3")

        result = cache.get("multi_list")
        assert len(result) == 3
        assert "item1" in result
        assert "item2" in result
        assert "item3" in result

    def test_lpush_unpack(self):
        """Test lpush with unpack=True."""
        cache = Cache()
        items = ["a", "b", "c"]
        cache.lpush("unpack_list", items, unpack=True)

        result = cache.get("unpack_list")
        assert len(result) == 3
        assert "a" in result
