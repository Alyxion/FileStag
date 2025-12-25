"""
Web fetching utilities for FileStag.
"""

from .web_cache import WebCache
from .fetch import (
    web_fetch,
    FROM_CACHE,
    STATUS_CODE,
    HEADERS,
    STORED_IN_CACHE,
)

__all__ = [
    "web_fetch",
    "WebCache",
    "FROM_CACHE",
    "STATUS_CODE",
    "HEADERS",
    "STORED_IN_CACHE",
]
