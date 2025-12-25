"""
Implements the class :class:`DiskCache` which allows you to fast and easy
store / dump data on disk and to quickly restore them afterwards with a simple
version management.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from typing import Any

from filestag._lock import StagLock
from filestag.file_stag import FileStag
from filestag.cache import _bundle

DEFAULT_CACHE_DIR = "./.stscache"
"The default caching directory if none is passed"

BUNDLE_EXTENSION = ".stbun"
"File extension for a FileStag bundle"


class DiskCache:
    """
    Helper class to persist data such as computation results on disk.

    This class is usually not used directly, see :class:`Cache` which makes
    use of the DiskCache. All elements you store with a beginning "$"
    using the **Cache** class will automatically be stored on disk, all
    entries without in memory.
    """

    def __init__(self, version: str | int = "1", cache_dir: str | None = None):
        """
        :param version: The cache version. 1 by default.

            When ever you change this version all old cache values will be
            removed and/or ignored from the cache.
        :param cache_dir: The directory in which the data shall be cached
        """
        if cache_dir is None:
            cache_dir = os.path.abspath(DEFAULT_CACHE_DIR)
        self.cache_dir = cache_dir
        self._version: str | int = version
        """
        The cache version.

        It is stored along all cache values stored on disk and only elements
        sharing the same version will be accepted.
        """
        self._access_lock = StagLock()
        "Multithread access lock"
        self.dir_created = False
        "Defines if the caching dir was already created"

    @property
    def version(self) -> str:
        """
        Returns the cache version.
        """
        return str(self._version)

    @staticmethod
    def encode_name(name: str) -> str:
        """
        Encodes the name of the object to be cached to a unique hash.

        :param name: The name of the data
        :return: The encoded name
        """
        encoded_name = hashlib.md5(name.encode("utf-8")).hexdigest()
        return encoded_name

    def get_cache_name(self, name: str) -> str:
        """
        Encodes the name of the object to be cached to a unique hash.

        :param name: The name of the data
        :return: The encoded name
        """
        encoded_name = f"{self.cache_dir}/{self.encode_name(name)}"
        return encoded_name

    def _ensure_cache_dir(self) -> None:
        """
        Verifies the caching directory is present.
        """
        with self._access_lock:
            if not self.dir_created:
                os.makedirs(self.cache_dir, exist_ok=True)

    def clear(self) -> None:
        """
        Clears the disk cache completely.
        """
        with self._access_lock:
            try:
                shutil.rmtree(self.cache_dir)
            except FileNotFoundError:
                pass

    def set(self, key: str, value: Any, version: int | str = 1) -> None:
        """
        Persists a single value in the cache.

        :param key: The name of the object to cache or a combination of
            key and version separated by an @ sign, e.g. "database@1"
        :param value: The element's value
        :param version: The cache version for this entry.
        """
        from filestag.cache.cache import Cache

        key, eff_version = Cache.get_key_and_version(key, self._version, version)
        with self._access_lock:
            params = {"__version": eff_version}
            self._ensure_cache_dir()
            cache_name = self.get_cache_name(key)
            bundle_fn = cache_name + BUNDLE_EXTENSION
            FileStag.save(cache_name, _bundle.bundle({"data": value, "version": 1}))
            FileStag.save(bundle_fn, _bundle.bundle(params))

    def get(self, key: str, version: int | str = 1, default: Any = None) -> Any | None:
        """
        Tries to read an element from the disk cache.

        :param key: The name of the object to load from cache or a combination
            of key and version separated by an @ sign, e.g. "database@1"
        :param version: The assumed version of this element we are searching
            for. If the version does not match the old entry is ignored.
        :param default: The default value to return if no cache entry could
            be found
        :return: Either the cache data or the default value as fallback
        """
        from filestag.cache.cache import Cache

        with self._access_lock:
            key, eff_version = Cache.get_key_and_version(key, self._version, version)
            cache_name = self.get_cache_name(key)
            params = {"__version": eff_version}
            stream_data = FileStag.load(cache_name)
            if stream_data is None:
                return default
            bundle_data = _bundle.unbundle(stream_data)
            if bundle_data.get("version", 0) != 1:
                return default
            data = bundle_data["data"]
            bundle_fn = cache_name + BUNDLE_EXTENSION
            if FileStag.exists(bundle_fn):
                bundle_file_data = FileStag.load(bundle_fn)
                if bundle_file_data:
                    stored_params = _bundle.unbundle(bundle_file_data)
                    if stored_params != params:
                        return default
            return data

    def delete(self, key: str) -> bool:
        """
        Deletes a single cache entry.

        :param key: The cache's key
        :return: True if the element was found and deleted
        """
        with self._access_lock:
            cache_name = self.get_cache_name(key)
            bundle_fn = cache_name + BUNDLE_EXTENSION
            FileStag.delete(bundle_fn)
            if FileStag.exists(cache_name):
                return FileStag.delete(cache_name)
            return False

    def __contains__(self, key: str) -> bool:
        from filestag.cache.cache import Cache

        with self._access_lock:
            key, eff_version = Cache.get_key_and_version(key, self._version)
            cache_name = self.get_cache_name(key)
            return FileStag.exists(cache_name)
