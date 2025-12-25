"""Tests for _env module."""

import os

import pytest

from filestag._env import insert_environment_data


class TestInsertEnvironmentData:
    """Tests for insert_environment_data function."""

    def test_no_env_vars(self):
        """Test string without environment variable placeholders."""
        text = "Hello, world!"
        result = insert_environment_data(text)
        assert result == "Hello, world!"

    def test_single_env_var(self):
        """Test string with a single environment variable."""
        os.environ["TEST_VAR"] = "test_value"
        try:
            text = "Hello, {{env.TEST_VAR}}!"
            result = insert_environment_data(text)
            assert result == "Hello, test_value!"
        finally:
            del os.environ["TEST_VAR"]

    def test_multiple_env_vars(self):
        """Test string with multiple environment variables."""
        os.environ["TEST_USER"] = "john"
        os.environ["TEST_PASS"] = "secret"
        try:
            text = "https://{{env.TEST_USER}}:{{env.TEST_PASS}}@example.com"
            result = insert_environment_data(text)
            assert result == "https://john:secret@example.com"
        finally:
            del os.environ["TEST_USER"]
            del os.environ["TEST_PASS"]

    def test_missing_env_var(self):
        """Test string with non-existent environment variable."""
        text = "Hello, {{env.NONEXISTENT_VAR_12345}}!"
        result = insert_environment_data(text)
        # Should leave the placeholder unchanged
        assert result == "Hello, {{env.NONEXISTENT_VAR_12345}}!"

    def test_mixed_existing_and_missing(self):
        """Test string with both existing and missing environment variables."""
        os.environ["TEST_EXISTS"] = "exists"
        try:
            text = "{{env.TEST_EXISTS}} and {{env.MISSING_VAR}}"
            result = insert_environment_data(text)
            assert result == "exists and {{env.MISSING_VAR}}"
        finally:
            del os.environ["TEST_EXISTS"]

    def test_same_var_multiple_times(self):
        """Test environment variable appearing multiple times."""
        os.environ["TEST_REPEAT"] = "X"
        try:
            text = "{{env.TEST_REPEAT}}-{{env.TEST_REPEAT}}-{{env.TEST_REPEAT}}"
            result = insert_environment_data(text)
            assert result == "X-X-X"
        finally:
            del os.environ["TEST_REPEAT"]

    def test_empty_string(self):
        """Test with empty string."""
        result = insert_environment_data("")
        assert result == ""

    def test_empty_env_value(self):
        """Test environment variable with empty value."""
        os.environ["TEST_EMPTY"] = ""
        try:
            text = "Value: {{env.TEST_EMPTY}}!"
            result = insert_environment_data(text)
            assert result == "Value: !"
        finally:
            del os.environ["TEST_EMPTY"]

    def test_special_characters_in_value(self):
        """Test environment variable with special characters."""
        os.environ["TEST_SPECIAL"] = "a=b&c=d"
        try:
            text = "Query: {{env.TEST_SPECIAL}}"
            result = insert_environment_data(text)
            assert result == "Query: a=b&c=d"
        finally:
            del os.environ["TEST_SPECIAL"]

    def test_partial_placeholder(self):
        """Test partial placeholders that should not be replaced."""
        text = "{{env.}}, {{env, env.VAR}}"
        result = insert_environment_data(text)
        # Since there's "{{env." in the string, it will process but not find matches
        assert result == text

    def test_uses_path_env(self):
        """Test with standard PATH environment variable."""
        # PATH should always exist
        text = "Path is: {{env.PATH}}"
        result = insert_environment_data(text)
        assert result == f"Path is: {os.environ['PATH']}"
