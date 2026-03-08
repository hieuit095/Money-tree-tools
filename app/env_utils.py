"""Shared dotenv-related utilities used by config_manager and igm_mapping."""

import re


def dotenv_escape(value: str) -> str:
    """Escape a value for safe inclusion in a .env file.

    Returns the value unquoted when it only contains safe characters,
    or double-quoted with backslash escaping otherwise.
    """
    if value == "":
        return ""
    if re.fullmatch(r"[A-Za-z0-9_./:@+-]+", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'
