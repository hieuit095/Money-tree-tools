from app.priority_manager import (
    DEFAULT_PRIORITY_SERVICES,
    effective_priority_services,
    parse_priority_services,
    serialize_priority_services,
)


def test_parse_priority_services_empty_returns_empty():
    assert parse_priority_services("") == set()
    assert parse_priority_services(None) == set()


def test_parse_priority_services_normalizes_and_dedupes():
    assert parse_priority_services(" Grass, WIPTER,grass ,, ") == {"grass", "wipter"}


def test_effective_priority_services_defaults_when_missing():
    assert effective_priority_services({"PRIORITY_SERVICES": ""}) == DEFAULT_PRIORITY_SERVICES


def test_serialize_priority_services_is_sorted_and_unique():
    raw = serialize_priority_services({"wipter", "grass", "grass"})
    assert raw == "grass,wipter"

