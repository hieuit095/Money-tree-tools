from typing import Any


DEFAULT_PRIORITY_SERVICES = {"grass", "wipter", "repocket", "honeygain"}


def parse_priority_services(raw: Any) -> set[str]:
    if raw is None:
        return set()
    text = str(raw).strip().lower()
    if not text:
        return set()
    items: set[str] = set()
    for part in text.split(","):
        name = part.strip().lower()
        if name:
            items.add(name)
    return items


def effective_priority_services(config: dict[str, str]) -> set[str]:
    parsed = parse_priority_services(config.get("PRIORITY_SERVICES"))
    return parsed or set(DEFAULT_PRIORITY_SERVICES)


def serialize_priority_services(services: set[str]) -> str:
    cleaned = []
    for s in services:
        name = str(s).strip().lower()
        if name:
            cleaned.append(name)
    cleaned = sorted(set(cleaned))
    return ",".join(cleaned)

