import pytest

from app.log_utils import parse_tail, truncate_utf8_text


def test_parse_tail_defaults():
    assert parse_tail(None) == 200
    assert parse_tail("") == 200
    assert parse_tail("   ") == 200


def test_parse_tail_valid():
    assert parse_tail("1") == 1
    assert parse_tail("2000") == 2000
    assert parse_tail("10", default=50) == 10


@pytest.mark.parametrize("value", ["0", "-1", "2001", "abc", "1.5"])
def test_parse_tail_invalid(value: str):
    with pytest.raises(ValueError):
        parse_tail(value)


def test_truncate_utf8_text_noop_when_small():
    text = "hello\nworld\n"
    assert truncate_utf8_text(text, max_bytes=1024) == text


def test_truncate_utf8_text_caps_output_bytes():
    text = "x" * 1000
    out = truncate_utf8_text(text, max_bytes=128)
    assert out.endswith("\n... (truncated)\n")
    assert len(out.encode("utf-8")) <= 128
