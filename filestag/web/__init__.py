"""
Web fetching utilities for FileStag.
"""

from .web_cache import WebCache
from .fetch import (
    web_fetch,
    web_fetch_async,
    FROM_CACHE,
    STATUS_CODE,
    HEADERS,
    STORED_IN_CACHE,
)

__all__ = [
    "web_fetch",
    "web_fetch_async",
    "WebCache",
    "FROM_CACHE",
    "STATUS_CODE",
    "HEADERS",
    "STORED_IN_CACHE",
]
