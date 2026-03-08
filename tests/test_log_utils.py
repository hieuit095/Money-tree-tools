"""Unit tests for app.log_utils."""

import pytest

from app.log_utils import parse_tail, truncate_utf8_text


class TestParseTail:
    def test_none_returns_default(self):
        assert parse_tail(None) == 200

    def test_empty_string_returns_default(self):
        assert parse_tail("") == 200
        assert parse_tail("  ") == 200

    def test_valid_integer(self):
        assert parse_tail("50") == 50
        assert parse_tail("1") == 1
        assert parse_tail("2000") == 2000

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError):
            parse_tail("0")
        with pytest.raises(ValueError):
            parse_tail("2001")

    def test_non_digit_raises(self):
        with pytest.raises(ValueError):
            parse_tail("abc")
        with pytest.raises(ValueError):
            parse_tail("-1")
        with pytest.raises(ValueError):
            parse_tail("3.14")

    def test_custom_defaults(self):
        assert parse_tail(None, default=100) == 100
        assert parse_tail("5", min_value=5, max_value=10) == 5
        with pytest.raises(ValueError):
            parse_tail("4", min_value=5, max_value=10)


class TestTruncateUtf8Text:
    def test_short_text_unchanged(self):
        text = "hello world"
        assert truncate_utf8_text(text, max_bytes=1000) == text

    def test_empty_text(self):
        assert truncate_utf8_text("", max_bytes=100) == ""

    def test_exact_boundary(self):
        text = "a" * 100
        result = truncate_utf8_text(text, max_bytes=100)
        assert result == text

    def test_truncation_adds_suffix(self):
        text = "a" * 200
        result = truncate_utf8_text(text, max_bytes=50)
        assert result.endswith("... (truncated)\n")
        assert len(result.encode("utf-8")) <= 50

    def test_unicode_safe_truncation(self):
        # Multibyte characters should not be mangled
        text = "日本語テスト" * 50
        result = truncate_utf8_text(text, max_bytes=100)
        # Should decode cleanly (no UnicodeDecodeError)
        result.encode("utf-8")
        assert "truncated" in result
