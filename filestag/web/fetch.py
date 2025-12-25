"""
The web_fetch module grants easy access to data in the web via its web_fetch
function, a one-liner to receive a file via http within a given timeout.
"""

from __future__ import annotations

from filestag._version import __version__
from .web_cache import WebCache

FROM_CACHE = "fromCache"
"Defines if the file was loaded from the local disk cache"
HEADERS = "headers"
"Defines the dictionary element containing the response's headers"
STATUS_CODE = "statusCode"
"The response http status code, e.g. 200"
STORED_IN_CACHE = "storedInCache"
"Defines if the file was added to the local disk cache"


def web_fetch(
    url: str,
    timeout_s: float = 10.0,
    max_cache_age: float = 0.0,
    cache: bool | None = None,
    filename: str | None = None,
    out_response_details: dict | None = None,
    all_codes: bool = False,
    **_,
) -> bytes | None:
    """
    Fetches a file from the web via HTTP GET

    :param url: The URL
    :param timeout_s: The timeout in seconds
    :param max_cache_age: The maximum cache age in seconds. Note that the
        internal cache is everything else than optimized so this should only be
        used to load e.g. the base data for an app once.
    :param cache: If set the default max cache age will be used
    :param filename: If specified the data will be stored in this file
    :param out_response_details: Dictionary target to retrieve response details
        such as
        * headers - The response headers
        * statusCode - The request's http status code
        * fromCache - Defines if the files was loaded from cache
        * storedInCache - Defines if the file was added to the cache
    :param all_codes: Defines if all http return codes shall be accepted.
        Pass a dictionary to response_details for the details.
    :return: The file's content if available and not timed out, otherwise None
    """
    from_cache = False
    if cache is not None and cache:
        max_cache_age = 24 * 60 * 60 * 7
    if max_cache_age != 0:
        data = WebCache.fetch(url, max_age=max_cache_age)
        if data is not None:
            if out_response_details is not None:
                out_response_details[FROM_CACHE] = True
            if filename is not None:
                with open(filename, "wb") as file:
                    file.write(data)
            return data
        else:
            if out_response_details is not None:
                out_response_details[FROM_CACHE] = False
    import requests

    headers = {
        "User-Agent": f"FileStag/{__version__} (https://github.com/scistag/filestag/)"
    }

    try:
        response = requests.get(url=url, timeout=timeout_s, headers=headers)
    except requests.exceptions.RequestException:
        return None
    if all_codes or response.status_code != 200:
        return None
    if max_cache_age != 0 and response.status_code == 200 and not from_cache:
        WebCache.store(url, response.content)
        if out_response_details is not None:
            out_response_details[STORED_IN_CACHE] = True
    if filename is not None:
        with open(filename, "wb") as file:
            file.write(response.content)
    if out_response_details is not None:
        out_response_details[STATUS_CODE] = response.status_code
        out_response_details[HEADERS] = response.headers
    return response.content


async def web_fetch_async(
    url: str,
    timeout_s: float = 10.0,
    max_cache_age: float = 0.0,
    cache: bool | None = None,
    filename: str | None = None,
    out_response_details: dict | None = None,
    all_codes: bool = False,
    **_,
) -> bytes | None:
    """
    Asynchronously fetches a file from the web via HTTP GET.

    :param url: The URL
    :param timeout_s: The timeout in seconds
    :param max_cache_age: The maximum cache age in seconds. Note that the
        internal cache is everything else than optimized so this should only be
        used to load e.g. the base data for an app once.
    :param cache: If set the default max cache age will be used
    :param filename: If specified the data will be stored in this file
    :param out_response_details: Dictionary target to retrieve response details
        such as
        * headers - The response headers
        * statusCode - The request's http status code
        * fromCache - Defines if the files was loaded from cache
        * storedInCache - Defines if the file was added to the cache
    :param all_codes: Defines if all http return codes shall be accepted.
        Pass a dictionary to response_details for the details.
    :return: The file's content if available and not timed out, otherwise None
    """
    import httpx
    import aiofiles

    from_cache = False
    if cache is not None and cache:
        max_cache_age = 24 * 60 * 60 * 7
    if max_cache_age != 0:
        data = await WebCache.fetch_async(url, max_age=max_cache_age)
        if data is not None:
            if out_response_details is not None:
                out_response_details[FROM_CACHE] = True
            if filename is not None:
                async with aiofiles.open(filename, "wb") as file:
                    await file.write(data)
            return data
        else:
            if out_response_details is not None:
                out_response_details[FROM_CACHE] = False

    headers = {
        "User-Agent": f"FileStag/{__version__} (https://github.com/scistag/filestag/)"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout_s, headers=headers)
    except httpx.RequestError:
        return None
    if all_codes or response.status_code != 200:
        return None
    if max_cache_age != 0 and response.status_code == 200 and not from_cache:
        await WebCache.store_async(url, response.content)
        if out_response_details is not None:
            out_response_details[STORED_IN_CACHE] = True
    if filename is not None:
        async with aiofiles.open(filename, "wb") as file:
            await file.write(response.content)
    if out_response_details is not None:
        out_response_details[STATUS_CODE] = response.status_code
        out_response_details[HEADERS] = dict(response.headers)
    return response.content


__all__ = [
    "web_fetch",
    "web_fetch_async",
    "FROM_CACHE",
    "STATUS_CODE",
    "HEADERS",
    "STORED_IN_CACHE",
]
