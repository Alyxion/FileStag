"""
Simplified bundler for cache serialization.

This is a simplified version that only supports JSON-serializable types
and bytes. It does not support pandas DataFrames or numpy arrays.
"""

from __future__ import annotations

import json
import base64
from typing import Any


BUNDLE_VERSION = 1
BYTES_MARKER = "__bytes__"


def _serialize_value(value: Any) -> Any:
    """
    Serializes a value to a JSON-compatible format.

    :param value: The value to serialize
    :return: The serialized value
    """
    if isinstance(value, bytes):
        return {BYTES_MARKER: base64.b64encode(value).decode("ascii")}
    elif isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_serialize_value(v) for v in value]
    elif isinstance(value, tuple):
        return {"__tuple__": [_serialize_value(v) for v in value]}
    elif isinstance(value, set):
        return {"__set__": [_serialize_value(v) for v in value]}
    else:
        return value


def _deserialize_value(value: Any) -> Any:
    """
    Deserializes a value from JSON format.

    :param value: The value to deserialize
    :return: The deserialized value
    """
    if isinstance(value, dict):
        if BYTES_MARKER in value:
            return base64.b64decode(value[BYTES_MARKER])
        elif "__tuple__" in value:
            return tuple(_deserialize_value(v) for v in value["__tuple__"])
        elif "__set__" in value:
            return set(_deserialize_value(v) for v in value["__set__"])
        else:
            return {k: _deserialize_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_deserialize_value(v) for v in value]
    else:
        return value


def bundle(data: dict) -> bytes:
    """
    Bundles data into a JSON-based format.

    :param data: The data to bundle (must be JSON-serializable or bytes)
    :return: The bundled data as bytes
    """
    serialized = _serialize_value(data)
    wrapper = {"version": BUNDLE_VERSION, "data": serialized}
    return json.dumps(wrapper).encode("utf-8")


def unbundle(data: bytes) -> dict:
    """
    Unbundles data from the JSON-based format.

    :param data: The bundled data
    :return: The original data
    """
    wrapper = json.loads(data.decode("utf-8"))
    if wrapper.get("version") != BUNDLE_VERSION:
        raise ValueError(f"Unsupported bundle version: {wrapper.get('version')}")
    return _deserialize_value(wrapper["data"])
