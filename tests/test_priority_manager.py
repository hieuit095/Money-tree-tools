"""Unit tests for app.priority_manager."""

import pytest

from app.priority_manager import (
    DEFAULT_PRIORITY_SERVICES,
    parse_priority_services,
    effective_priority_services,
    serialize_priority_services,
)


class TestParsePriorityServices:
    def test_none_returns_empty(self):
        assert parse_priority_services(None) == set()

    def test_empty_string_returns_empty(self):
        assert parse_priority_services("") == set()
        assert parse_priority_services("   ") == set()

    def test_single_service(self):
        assert parse_priority_services("grass") == {"grass"}

    def test_multiple_services(self):
        result = parse_priority_services("grass,wipter,repocket")
        assert result == {"grass", "wipter", "repocket"}

    def test_whitespace_handling(self):
        result = parse_priority_services("  grass , wipter , repocket  ")
        assert result == {"grass", "wipter", "repocket"}

    def test_case_insensitive(self):
        result = parse_priority_services("GRASS,Wipter")
        assert result == {"grass", "wipter"}

    def test_duplicates_collapsed(self):
        result = parse_priority_services("grass,grass,wipter")
        assert result == {"grass", "wipter"}

    def test_empty_segments_ignored(self):
        result = parse_priority_services("grass,,wipter,")
        assert result == {"grass", "wipter"}


class TestEffectivePriorityServices:
    def test_returns_parsed_when_set(self):
        config = {"PRIORITY_SERVICES": "honeygain,grass"}
        result = effective_priority_services(config)
        assert result == {"honeygain", "grass"}

    def test_returns_defaults_when_empty(self):
        config = {"PRIORITY_SERVICES": ""}
        result = effective_priority_services(config)
        assert result == DEFAULT_PRIORITY_SERVICES

    def test_returns_defaults_when_missing(self):
        config = {}
        result = effective_priority_services(config)
        assert result == DEFAULT_PRIORITY_SERVICES


class TestSerializePriorityServices:
    def test_empty_set(self):
        assert serialize_priority_services(set()) == ""

    def test_single_service(self):
        assert serialize_priority_services({"grass"}) == "grass"

    def test_sorted_output(self):
        result = serialize_priority_services({"wipter", "grass", "bitping"})
        assert result == "bitping,grass,wipter"

    def test_case_normalization(self):
        result = serialize_priority_services({"GRASS", "Wipter"})
        assert result == "grass,wipter"

    def test_whitespace_stripped(self):
        result = serialize_priority_services({"  grass  ", " wipter"})
        assert result == "grass,wipter"

    def test_roundtrip(self):
        original = {"grass", "wipter", "honeygain"}
        serialized = serialize_priority_services(original)
        parsed_back = parse_priority_services(serialized)
        assert parsed_back == original
