"""
Web cache for temporary storage of downloaded files.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import tempfile
import time
from threading import RLock


def file_age_in_seconds(pathname: str) -> float:
    """
    Returns the age of a file in seconds

    :param pathname: The file's path
    :return: The age in seconds
    """
    stat = os.stat(pathname)
    return time.time() - stat.st_mtime


class WebCache:
    """
    The WebCache class allows the temporary storage of downloaded files in
    the temp directory. How long the file is rated as "valid" can be passed via
    (for example) the web_fetch function's cache duration parameter.
    """

    lock = RLock()
    "Access lock"
    cache_dir = tempfile.gettempdir() + "/filestag/"
    "The cache directory"
    app_name = "filestag"
    "The application's name"
    max_general_age = 60 * 60 * 7
    "The maximum age of any file loaded via the cache"
    max_cache_size = 200000000
    "The maximum file size in the cache"
    total_size = 0
    "Total cache size"
    files_stored = 0
    "Files stored in this session"
    cleaned = False
    "Defines if the cache was cleaned yet"

    @classmethod
    def set_app_name(cls, name: str) -> None:
        """
        Modifies the application's name (and thus the cache path)

        :param name: The application's name
        """
        with cls.lock:
            cls.app_name = name
            cls.cache_dir = tempfile.gettempdir() + f"/filestag/{name}/"
            os.makedirs(cls.cache_dir, exist_ok=True)
            cls.cleanup()

    @classmethod
    def fetch(cls, url: str, max_age: float) -> bytes | None:
        """
        Tries to fetch a file from the cache

        :param url: The original url
        :param max_age: The maximum age in seconds
        :return: On success the file's content
        """
        encoded_name = cls.encoded_name(url)
        full_name = cls.cache_dir + encoded_name
        try:
            with cls.lock:
                if os.path.exists(full_name):
                    if file_age_in_seconds(full_name) <= max_age:
                        with open(full_name, "rb") as f:
                            return f.read()
                    cls.remove_outdated_file(full_name)
                return None
        except FileNotFoundError:
            return None

    @classmethod
    def remove_outdated_file(cls, full_name: str) -> None:
        """
        Removes an outdated file from the cache

        :param full_name: The file's name
        """
        cls.total_size -= os.stat(full_name).st_size
        os.remove(full_name)

    @staticmethod
    def encoded_name(name: str) -> str:
        """
        Encodes a filename

        :param name: The filename
        :return: The encoded filename
        """
        return hashlib.md5(name.encode("utf-8")).hexdigest()

    @classmethod
    def find(cls, url: str) -> str | None:
        """
        Searches for a file in the cache and returns its disk path

        :param url: The http url of the file to search for
        :return: The file name if the file could be found
        """
        encoded_name = cls.encoded_name(url)
        full_name = cls.cache_dir + encoded_name
        if os.path.exists(full_name):
            return full_name
        return None

    @classmethod
    def store(cls, url: str, data: bytes) -> None:
        """
        Caches the new web element on disk.

        :param url: The url of the file being stored
        :param data: The data of the file being stored as bytes string
        """
        if not cls.cleaned:
            WebCache.cleanup()
        with cls.lock:
            cls.files_stored += 1
            if cls.files_stored == 1:
                os.makedirs(cls.cache_dir, exist_ok=True)
            if cls.total_size >= cls.max_cache_size:
                cls.flush()
            encoded_name = cls.encoded_name(url)
            full_name = cls.cache_dir + encoded_name
            with open(full_name, "wb") as file:
                file.write(data)
            cls.total_size += len(data)

    @classmethod
    def cleanup(cls) -> None:
        """
        Cleans up the cache and removes old files
        """
        with cls.lock:
            cls.cleaned = True
            try:
                files = os.listdir(cls.cache_dir)
            except FileNotFoundError:
                files = []
            cur_time = time.time()
            cls.total_size = 0
            for cur_file in files:
                full_name = cls.cache_dir + cur_file
                stat = os.stat(full_name)
                if os.path.isdir(full_name):
                    continue
                if cur_time - stat.st_mtime > cls.max_general_age:
                    os.remove(full_name)
                else:
                    cls.total_size += stat.st_size
            if cls.total_size >= cls.max_cache_size:
                cls.flush()

    @classmethod
    def flush(cls) -> None:
        """
        Clean the cache completely
        """
        with cls.lock:
            cls.total_size = 0
            try:
                shutil.rmtree(cls.cache_dir)
            except FileNotFoundError:
                pass
            os.makedirs(cls.cache_dir, exist_ok=True)

    # Async variants
    _async_lock: asyncio.Lock | None = None

    @classmethod
    def _get_async_lock(cls) -> asyncio.Lock:
        """Get or create the async lock."""
        if cls._async_lock is None:
            cls._async_lock = asyncio.Lock()
        return cls._async_lock

    @classmethod
    async def fetch_async(cls, url: str, max_age: float) -> bytes | None:
        """
        Asynchronously tries to fetch a file from the cache.

        :param url: The original url
        :param max_age: The maximum age in seconds
        :return: On success the file's content
        """
        import aiofiles
        import aiofiles.os

        encoded_name = cls.encoded_name(url)
        full_name = cls.cache_dir + encoded_name
        try:
            async with cls._get_async_lock():
                if await aiofiles.os.path.exists(full_name):
                    if file_age_in_seconds(full_name) <= max_age:
                        async with aiofiles.open(full_name, "rb") as f:
                            return await f.read()
                    await cls.remove_outdated_file_async(full_name)
                return None
        except FileNotFoundError:
            return None

    @classmethod
    async def remove_outdated_file_async(cls, full_name: str) -> None:
        """
        Asynchronously removes an outdated file from the cache.

        :param full_name: The file's name
        """
        import aiofiles.os

        stat = await aiofiles.os.stat(full_name)
        cls.total_size -= stat.st_size
        await aiofiles.os.remove(full_name)

    @classmethod
    async def store_async(cls, url: str, data: bytes) -> None:
        """
        Asynchronously caches the new web element on disk.

        :param url: The url of the file being stored
        :param data: The data of the file being stored as bytes string
        """
        import aiofiles
        import aiofiles.os

        if not cls.cleaned:
            await cls.cleanup_async()
        async with cls._get_async_lock():
            cls.files_stored += 1
            if cls.files_stored == 1:
                await aiofiles.os.makedirs(cls.cache_dir, exist_ok=True)
            if cls.total_size >= cls.max_cache_size:
                await cls.flush_async()
            encoded_name = cls.encoded_name(url)
            full_name = cls.cache_dir + encoded_name
            async with aiofiles.open(full_name, "wb") as file:
                await file.write(data)
            cls.total_size += len(data)

    @classmethod
    async def cleanup_async(cls) -> None:
        """
        Asynchronously cleans up the cache and removes old files.
        """
        import aiofiles.os

        async with cls._get_async_lock():
            cls.cleaned = True
            try:
                files = await aiofiles.os.listdir(cls.cache_dir)
            except FileNotFoundError:
                files = []
            cur_time = time.time()
            cls.total_size = 0
            for cur_file in files:
                full_name = cls.cache_dir + cur_file
                stat = await aiofiles.os.stat(full_name)
                if await aiofiles.os.path.isdir(full_name):
                    continue
                if cur_time - stat.st_mtime > cls.max_general_age:
                    await aiofiles.os.remove(full_name)
                else:
                    cls.total_size += stat.st_size
            if cls.total_size >= cls.max_cache_size:
                await cls.flush_async()

    @classmethod
    async def flush_async(cls) -> None:
        """
        Asynchronously cleans the cache completely.
        """
        import aiofiles.os

        async with cls._get_async_lock():
            cls.total_size = 0
            try:
                await asyncio.to_thread(shutil.rmtree, cls.cache_dir)
            except FileNotFoundError:
                pass
            await aiofiles.os.makedirs(cls.cache_dir, exist_ok=True)
