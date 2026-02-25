from __future__ import annotations


def parse_tail(value: str | None, *, default: int = 200, min_value: int = 1, max_value: int = 2000) -> int:
    if value is None or str(value).strip() == "":
        return default
    raw = str(value).strip()
    if not raw.isdigit():
        raise ValueError("tail must be an integer")
    tail = int(raw)
    if tail < min_value or tail > max_value:
        raise ValueError("tail out of range")
    return tail


def truncate_utf8_text(text: str, *, max_bytes: int) -> str:
    data = text.encode("utf-8", errors="replace")
    if len(data) <= max_bytes:
        return text
    suffix = "\n... (truncated)\n"
    suffix_bytes = suffix.encode("utf-8")
    keep = max(0, max_bytes - len(suffix_bytes))
    clipped = data[:keep].decode("utf-8", errors="ignore")
    return clipped + suffix
