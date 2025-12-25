"""
Implements the :class:`Cache` class which allows easy caching data on disk
and in memory to minimize repetitive downloads and re-computations.
"""

from __future__ import annotations

import time
from fnmatch import fnmatch
from typing import Any, Callable, TYPE_CHECKING

from filestag._lock import StagLock
from filestag.cache.cache_ref import CacheRef

if TYPE_CHECKING:
    from filestag.cache.cache_ref import CacheRef

LIST_APPEND_PREFIX = "@L+"
"""Prefix to flag async updates as a list extension"""

DISK_CACHE_HEADER = "$"


class Cache:
    """
    The Cache class shall help caching computation results, downloaded data
    but also objects with large wind-up time (such as neural networks) between
    execution sessions.

    ..  code-block: python

        # caching in memory without version
        my_cache = Cache()
        def complex_computation():
            time.sleep(5.0) # just as dummy
            return {"result": 42}
        def rendering_function()
            global my_cache
            my_data = my_cache.cache("data", complex_computation)
            display(my_data)

        rendering_function()  # will take 5.0 seconds on the first run
        rendering_function()  # 0 seconds as "data" will be found in the cache

        # with version - all cache entries !=5 will be ignored
        my_cache = Cache(version=5)  # only cache entries with 5 will be valid
        ...

        # with per-element or "sub"-version.
        # the cache will always combine the cache object's version and the
        # version of the element. So in this case to "5.4"
        def rendering_function()
            global my_cache
            my_data = my_cache.cache("data@4", complex_computation)
            # or
            # my_data = my_cache.cache("data", complex_computation, version=4)
            display(my_data)

        # caching on disk between execution runs
        # if you run the cache "manually" you have to set a version number to
        # cache data between multiple execution sessions on disk.
        my_data = my_cache.cache("$data@5", complex_computation)

    If you pass a version of 0 the :meth:`get_app_session_id` will
    be used instead which will usually change on every restart except
    you set it yourself via set_app_session_id or are using a smart
    autoreloader.
    """

    _app_session_id: int = int(time.time() * 1000)
    """
    The current run's session ID. is updated every re-start usually, may
    be stored and restored by helper classes between application restarts.
    """

    def __init__(self, version: str | int = 1, cache_dir: str | None = None):
        """
        :param version: The cache version. 1 by default.

            When ever you change this version all old cache values will be
            removed and/or ignored from the cache.
        :param cache_dir: The directory in which the cache data shall be stored
        """
        self._access_lock = StagLock()
        "Multithreading access lock"
        self._mem_cache: dict = {}
        """
        A cache for temporary data storage and objects with a life time bound to
        this component's usage state.
        """
        self._mem_cache_versions: dict = {}
        "Version numbers for the elements stored in the memory cache"
        self._async_inbox: dict = {}
        """Elements which are staged for an update and will be applied once the owner
        of the cache fetches them via async_fetch"""

        from filestag.cache.disk_cache import DiskCache

        self._disk_cache = DiskCache(version=version, cache_dir=cache_dir)
        "Cache for persisting data between execution sessions"
        self._version = version
        """
        The cache version.

        It is stored along all cache values stored on disk and only elements
        sharing the same version will be accepted.
        """
        self.loaded = False
        "Defines if the component was correctly loaded"
        self._is_loading = False
        """
        Flag which tells if the component is currently being loaded and if new
        values added to the cache via ``self["objectName"]`` shall be flagged as
        volatile.
        """
        self._volatile_cache_entries: set = set()
        """
        Stores which cache entries shall be deleted upon the execution of
        :meth:`unload`.
        """
        self._key_revisions: dict = {}
        """
        Version counter for each key
        """

    @property
    def version(self) -> str:
        """
        Returns the cache version.
        """
        return str(self._version)

    @classmethod
    def get_app_session_id(cls) -> int:
        """
        Returns the app session id which is generated upon each application
        restart.
        """
        return cls._app_session_id

    @classmethod
    def override_app_session_id(cls, session_id: int) -> None:
        """
        Manually overrides the application's session ID.

        Should only be used by application session managers.

        :param session_id: The new session id
        """
        cls._app_session_id = session_id

    @classmethod
    def get_key_and_version(
        cls, key: str, major: str | int, minor: str | int | None = None
    ) -> tuple[str, str]:
        """
        Returns the effective key, version combination to search for a key in
        combination with the cache's and the element's version.

        :param key: The key (potentially still containing @version at its end),
            either "key" or "key@version", e.g. "myDb@2".
        :param major: The major version (provided by the cache object)
        :param minor: The minor version, per element.

            Default 0 for memory cache elements and 1 for disk cache entries.
        :return: The effective key and version with which the element shall be
            persisted and which we assume upon restore.
        """
        if minor is None:
            minor = 1 if DISK_CACHE_HEADER in key else 0
        if "@" in key:
            split_val = key.split("@")
            assert len(split_val) == 2
            key = split_val[0]
            minor = split_val[1]
        minor = str(minor)
        if minor == "0":  # session id only as cache version
            return key, f"{major}.{cls._app_session_id}"
        if minor.startswith("-"):  # minor only
            return key, f"{minor}"
        return key, f"{major}.{minor}"

    def cache(self, key: str, generator: Callable, *args, **kwargs) -> Any:
        """
        Tries to find the element **key** in the cache and returns its
        content. If no element with such a name and/or version number can be
        found **generator** will be called to generate the data, store it in the
        cache for the next execution.

        :param key: The key of the cache element
        :param generator: The function to call if the element is not stored
            in the cache yet.
        :keyword version: The version to assign to the cache entry.
        :keyword hash_val: A single value to be hashed and added to the version
            number to automatically invalidate it if the value changed.
        :param args: Argument parameters to be passed into the generator
        :param kwargs: Keyword parameter to be passed into the generator
        :return: The cached or newly created content
        """
        hash_val = kwargs.pop("hash_val", None)
        version = kwargs.pop("version", None)
        if hash_val is not None:
            version = str(version) if version else "0"
            version += "#" + str(hash_val)
        arg_list = list(args)
        # try to fetch from cache
        with self._access_lock:
            old_value = self.get(key, version=version)
            if old_value is not None:  # cached? fine
                return old_value
        new_data = generator(*arg_list, **kwargs)
        # update cache otherwise
        with self._access_lock:
            self.set(key, new_data, version=version)
            return new_data

    def set(
        self, key: str, value: Any, version: str | int | None = None, keep: bool = False
    ) -> Any:
        """
        Adds an item to the cache or updates it.

        :param key: The item's name
        :param value: The value to assign
        :param version: The version of the cache element.
        :param keep: If set to True the version will not be updated if the
            key does already exist and has an equal value
        :return: The assigned value
        """
        with self._access_lock:
            org_key = key
            key, eff_version = self.get_key_and_version(
                key, self._version, minor=version
            )
            assert len(key) > 0
            if (
                not key[0].isalpha()
                and not key.startswith(DISK_CACHE_HEADER)
                and not key.startswith("_")
            ):
                raise ValueError("Keys has to start with a character")
            if key in self._key_revisions:
                if keep:
                    if self[org_key] == value:
                        return value
                self._key_revisions[key] += 1
            else:
                self._key_revisions[key] = 1
            if key.startswith(DISK_CACHE_HEADER):
                self._disk_cache.set(org_key, value, version=version)
                return value
            # flag as volatile if added during loading process
            if key not in self._mem_cache and self._is_loading:
                self._volatile_cache_entries.add(key)
            self._mem_cache[key] = value
            self._mem_cache_versions[key] = eff_version
            return value

    def set_async(self, key: str, value: Any) -> None:
        """
        Stages an update for the cache which will be applied once the owner thread of
        the cache regains control and fetches them via :meth:`async_fetch`.

        :param key: The key to be updated
        :param value: The key's new value
        """
        with self._access_lock:
            self._async_inbox[key] = value

    def get(
        self, key: str, default: Any = None, version: str | int | None = None
    ) -> Any:
        """
        Returns a value from the cache.

        :param key: The item's name.
        :param version: The cache element's version.
        :param default: The value to return by default if no cache element
            could be found.
        :return: The item's value.
        """
        with self._access_lock:
            org_key = key
            key, eff_version = self.get_key_and_version(
                key, self._version, minor=version
            )
            if key.startswith(DISK_CACHE_HEADER):
                data = self._disk_cache.get(org_key, version=version)
                if data is None:
                    return default
                return data
            if key in self._mem_cache and self._mem_cache_versions[key] == eff_version:
                return self._mem_cache[key]
            else:
                return default

    def get_revision(self, key: str) -> int:
        """
        Returns the revision of given cache entry.

        :param key: The key of the version to return
        :return: The revision. 0 if the key does not exist.
        """
        with self._access_lock:
            return self._key_revisions.get(key, 0)

    def async_fetch(self) -> None:
        """
        Applies all values staged via async_set and lpush_async, e.g. from a
        remote thread.
        """
        with self._access_lock:
            for key, value in self._async_inbox.items():
                if key.startswith(LIST_APPEND_PREFIX):
                    key = key[len(LIST_APPEND_PREFIX):]
                    self.lpush(key, value, unpack=True)
                else:
                    self.set(key, value)
            self._async_inbox = {}

    def clear(self) -> None:
        """
        Clears the disk cache completely.
        """
        with self._access_lock:
            self._mem_cache = {}
            self._mem_cache_versions = {}
        self._disk_cache.clear()

    def load(self) -> None:
        """
        Call this before you start using a component for the first time.
        """
        with self._access_lock:
            if self.loaded:
                raise RuntimeError("Tried to load component twice")
            self._is_loading = True
            self.handle_load()
            if not self.loaded:
                raise RuntimeError(
                    "loaded flag of component not correctly set to True. "
                    "Did you forget to call super().handle_load()?"
                )

    def unload(self) -> None:
        """
        Call this to unload all data from your component which was created
        during the handle_load execution.
        """
        with self._access_lock:
            if not self.loaded:
                raise RuntimeError(
                    "Tried to unload component which was not loaded before"
                )
            self.handle_unload()
            if self.loaded:
                raise RuntimeError(
                    "loaded flag of component not correctly set to False. "
                    "Did you forget to call super().handle_unload()?"
                )
            for element in self._volatile_cache_entries:
                if element.startswith("."):  # clear volatile members
                    member_name = element[1:]
                    self.__dict__[member_name] = None
                # delete volatile cache entries
                elif element in self._mem_cache:
                    del self._mem_cache[element]
                    del self._mem_cache_versions[element]
                    self._key_revisions[element] += 1

    def get_is_loading(self) -> bool:
        """
        Returns if the component is currently being loaded.
        """
        with self._access_lock:
            return self._is_loading

    def handle_load(self) -> None:
        """
        Event handling function for dynamically loading data on demand.
        """
        with self._access_lock:
            self.loaded = True

    def handle_unload(self) -> None:
        """
        Event handler for unloading elements previously loaded.
        """
        with self._access_lock:
            self.loaded = False

    def add_volatile_member(self, name: str) -> None:
        """
        Adds a member to the volatile cache entry variable list.

        :param name: The name of the member variable to be added.
        """
        with self._access_lock:
            self._volatile_cache_entries.add("." + name)

    def __setitem__(self, key: str, value: Any) -> Any:
        self.set(key, value)
        return value

    def __getitem__(self, key: str) -> Any:
        with self._access_lock:
            result = self.get(key)
            if (
                result is None
                and key not in self._mem_cache
                and key not in self._disk_cache
            ):
                raise KeyError(f"Key {key} not found")
            return result

    def inc(self, key: str, value: float | int = 1) -> float | int:
        """
        Increases given cache value.

        :param key: The key to increase
        :param value: The value by which the value shall be increased
        :return: The new value
        """
        with self._access_lock:
            if key in self:
                new_value = self[key] + value
                self[key] = new_value
                return new_value
            else:
                self[key] = value
                return value

    def dec(self, key: str, value: float | int) -> float | int:
        """
        Decreases given cache value.

        :param key: The key to decrease
        :param value: The value by which the value shall be decreased
        :return: The new value
        """
        with self._access_lock:
            if key in self:
                new_value = self[key] - value
                self[key] = new_value
                return new_value
            else:
                self[key] = -value
                return -value

    def lpush(self, key: str, *args, unpack: bool = False) -> None:
        """
        Appends the value provided to the list named key.

        :param key: The key of the list
        :param args: The value or values to be added
        :param unpack: Defines if value is a list and all elements shall be added
        """
        if len(args) == 1:
            value = args[0]
        else:
            value = list(args)
            unpack = True
        with self._access_lock:
            if key in self:
                tar_list = self[key]
                self.increase_revision(key, True)
            else:
                tar_list = []
                self[key] = tar_list
            if not isinstance(tar_list, list):
                raise ValueError(f"Tried to append new values to non-list element {key}")
            if unpack:
                if not isinstance(value, list):
                    raise ValueError("Can only unpack lists")
                tar_list.extend(value)
            else:
                tar_list.append(value)

    def lpush_async(self, key: str, value: Any) -> None:
        """
        Adds an entry to the list as soon as the owning thread regains control.

        :param key: The key of the list
        :param value: The element to be added
        """
        with self._access_lock:
            list_key = f"{LIST_APPEND_PREFIX}{key}"
            if list_key in self._async_inbox:
                self._async_inbox[list_key].append(value)
            else:
                self._async_inbox[list_key] = [value]

    def lpop(self, key: str, index: int = 0, count: int = 1) -> list:
        """
        Pops one or multiple values from the list.

        :param key: The key of the list
        :param index: The index from which to receive. 0 = front, -1 = end.
        :param count: The count of values to pop. -1 = all values.
        :return: A list of all values received.
        """
        if count == 0:
            return []
        if count < 0:
            raise ValueError("Passed negative count argument")
        with self._access_lock:
            if key not in self:
                return []
            src_list = self[key]
            if not isinstance(src_list, list):
                raise ValueError(f"Tried to pop values from non-list element {key}")
            if count >= len(src_list) or count == -1:
                results = src_list
                self[key] = []
            else:
                if index == -count:
                    results = src_list[-count:]
                    end = len(src_list) - count
                    self[key] = src_list[0:end]
                elif index == 0:
                    results = src_list[0:count]
                    self[key] = src_list[count:]
                else:
                    raise ValueError(
                        "Indices other than 0 and -count currently not supported"
                    )
            return results

    def pop(self, key: str, default: Any = None, index: int = 0) -> Any | None:
        """
        Tries to receive a single value from the cache.

        :param key: The key to search for
        :param default: The default value
        :param index: The index from which to receive. 0 = front, -1 = end.
        :return: The value
        """
        with self._access_lock:
            if key not in self:
                return default
            element = self.get(key)
            if isinstance(element, list):
                result = self.lpop(key, index=index, count=1)
                if len(result) > 0:
                    return result[0]
                return default
            del self[key]
            return element

    def llen(self, key: str) -> int:
        """
        Receives the length of the list with given name.

        :param key: The list's name in the cache
        :return: The list's length if the list is known, 0 otherwise.
        """
        with self._access_lock:
            if key not in self:
                return 0
            src_list = self[key]
            if not isinstance(src_list, list):
                raise ValueError(f"Tried to receive length of non-list element {key}")
            return len(src_list)

    def increase_revision(self, key: str, _already_locked: bool = False) -> int:
        """
        Increases the version of given key.

        :param key: The key to modify
        :param _already_locked: Defines if we are already locked
        :return: The new version
        """
        if _already_locked:
            self._key_revisions[key] += 1
            return self._key_revisions[key]
        else:
            with self._access_lock:
                self._key_revisions[key] += 1
                return self._key_revisions[key]

    def remove(self, keys: str | list[str]) -> int:
        """
        Removes the key or keys matching the name or name mask provided.

        :param keys: A single name or a list of names of keys to remove.
        :return: The number of elements deleted
        """
        with self._access_lock:
            if isinstance(keys, str):
                keys = [keys]
            remove_set: set = set()
            for element in keys:
                if "?" in element or "*" in element:
                    for cur_key in self._key_revisions.keys():
                        if fnmatch(cur_key, element):
                            remove_set.add(cur_key)
                else:
                    if element in self._key_revisions:
                        remove_set.add(element)
            for element in remove_set:
                if element in self:
                    del self[element]
            return len(remove_set)

    def non_zero(self, key: str) -> bool:
        """
        Returns if the element has a non-zero size.

        :param key: The key of the element to check
        :return: True if the element exists and has a size or length > 0
        """
        with self._access_lock:
            if key not in self:
                return False
            element = self[key]
            if element is None:
                return False
            if isinstance(element, (float, bool, int)):
                return element != 0
            if isinstance(element, (str, dict, list, bytes, tuple)):
                return len(element) > 0
            if hasattr(element, "shape"):  # np.ndarray and DataFrame
                return element.shape[0] > 0
            return True  # by default True (it exists)

    def create_ref(self, key: str, update_async: bool = False) -> "CacheRef":
        """
        Creates a reference to a single cache entry.

        :param key: The name of the key which shall be referred
        :param update_async: Defines if the value shall be updated asynchronously
        """
        return CacheRef(name=key, update_async=update_async, cache=self)

    def eval(self, statement: str) -> Any:
        """
        Evaluates a simple comparison statement and returns its result.

        :param statement: The statement to be evaluated
        :return: The evaluation's result
        """
        compare = "=="
        assert compare in statement
        values = statement.split(compare)
        assert len(values) == 2
        key_value = self.get(values[0], "")
        if isinstance(key_value, int):
            return key_value == int(values[1])
        if isinstance(key_value, float):
            return key_value == float(values[1])
        if isinstance(key_value, bool):
            val = values[1].replace("True", "1").replace("False", "0")
            return key_value == int(val)
        return key_value == values[1]

    def __delitem__(self, key: str) -> None:
        """
        Deletes an element from the cache.

        :param key: The element's name
        """
        with self._access_lock:
            key, eff_version = self.get_key_and_version(key, self._version)
            if key.startswith(DISK_CACHE_HEADER):
                self._disk_cache.delete(key)
                return
            if key not in self._mem_cache:
                raise KeyError("Key not found")
            del self._mem_cache[key]
            self._key_revisions[key] += 1

    def __contains__(self, key: str) -> bool:
        """
        Returns if an element exists in the cache.

        :param key: The item's name
        :return: True if the item exists.
        """
        with self._access_lock:
            key, eff_version = self.get_key_and_version(key, self._version)
            if key.startswith(DISK_CACHE_HEADER):
                return key in self._disk_cache
            return (
                key in self._mem_cache and self._mem_cache_versions[key] == eff_version
            )

    def __enter__(self) -> "Cache":
        """Locks the cache to ensure no other threads reads it while it's updated."""
        self._access_lock.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Unlocks the cache."""
        self._access_lock.__exit__(exc_type, exc_val, exc_tb)


_cache_access_lock = StagLock()
"Cache creation lock"
_global_cache: Cache | None = None
"Shared, singleton global cache"


def get_global_cache() -> Cache:
    """
    Returns the shared global cache class.

    :return: The global cache
    """
    global _global_cache
    with _cache_access_lock:
        if _global_cache is None:
            _global_cache = Cache()
        return _global_cache
