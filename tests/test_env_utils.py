"""Unit tests for app.env_utils."""

import pytest

from app.env_utils import dotenv_escape


class TestDotenvEscape:
    def test_empty_string(self):
        assert dotenv_escape("") == ""

    def test_simple_alphanumeric(self):
        assert dotenv_escape("hello123") == "hello123"

    def test_safe_special_chars(self):
        # These characters are considered safe and not quoted
        assert dotenv_escape("user@example.com") == "user@example.com"
        assert dotenv_escape("linux/arm64") == "linux/arm64"
        assert dotenv_escape("key_value") == "key_value"
        assert dotenv_escape("a.b.c") == "a.b.c"
        assert dotenv_escape("a+b-c") == "a+b-c"
        assert dotenv_escape("host:8080") == "host:8080"

    def test_spaces_get_quoted(self):
        result = dotenv_escape("hello world")
        assert result == '"hello world"'

    def test_special_chars_get_quoted(self):
        result = dotenv_escape("pass#word")
        assert result.startswith('"')
        assert result.endswith('"')

    def test_backslash_escaped(self):
        result = dotenv_escape("path\\to\\file")
        assert "\\\\" in result

    def test_double_quote_escaped(self):
        result = dotenv_escape('say "hello"')
        assert '\\"' in result

    def test_newline_escaped(self):
        result = dotenv_escape("line1\nline2")
        assert "\\n" in result
        assert "\n" not in result  # actual newline should be gone
