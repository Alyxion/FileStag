"""
Helper functions to handle environment variables.
"""

import os


def insert_environment_data(text: str) -> str:
    """
    Searches for double curly brackets inside string followed by env.
    All occurrences for which an environment exists will be replaced with
    the environment variables content.

    Example: https://{{env.username}}:{{env.password}}@myserver.com

    will insert the environment variables username and password inside
    the string.

    :param text: The text to search within
    :return: The string into which the environment variables were inserted
    """
    if "{{env." not in text:
        return text
    for key, value in os.environ.items():
        search_token = "{{env." + key + "}}"
        text = text.replace(search_token, value)
    return text
