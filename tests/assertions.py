"""Lightweight assertion helpers for tests."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, TypeVar


T = TypeVar("T")


class AssertionBuilder:
    """Provides fluent-style assertions without external dependencies."""

    def __init__(self, actual: T) -> None:
        self.actual = actual

    def is_equal_to(self, expected: Any) -> "AssertionBuilder":
        assert self.actual == expected, (
            f"Expected {expected!r} but received {self.actual!r}."
        )
        return self

    def is_true(self) -> "AssertionBuilder":
        assert bool(self.actual) is True, (
            f"Expected value to be truthy but received {self.actual!r}."
        )
        return self

    def is_false(self) -> "AssertionBuilder":
        assert bool(self.actual) is False, (
            f"Expected value to be falsy but received {self.actual!r}."
        )
        return self

    def is_instance_of(self, expected_type: type) -> "AssertionBuilder":
        assert isinstance(self.actual, expected_type), (
            f"Expected instance of {expected_type!r} but received {type(self.actual)!r}."
        )
        return self

    def is_not_empty(self) -> "AssertionBuilder":
        if isinstance(self.actual, (Sequence, Mapping, set, frozenset)):
            assert len(self.actual) > 0, "Expected collection to be non-empty."
            return self
        if isinstance(self.actual, Iterable):
            assert any(True for _ in self.actual), "Expected iterable to be non-empty."
            return self
        raise AssertionError("is_not_empty requires an iterable value.")

    def is_empty(self) -> "AssertionBuilder":
        if isinstance(self.actual, (Sequence, Mapping, set, frozenset)):
            assert len(self.actual) == 0, "Expected collection to be empty."
            return self
        if isinstance(self.actual, Iterable):
            assert not any(True for _ in self.actual), "Expected iterable to be empty."
            return self
        raise AssertionError("is_empty requires an iterable value.")

    def contains(self, expected: Any) -> "AssertionBuilder":
        if isinstance(self.actual, Mapping):
            assert expected in self.actual, (
                f"Expected mapping to contain key {expected!r}."
            )
            return self
        if isinstance(self.actual, Iterable):
            assert expected in self.actual, (
                f"Expected iterable to contain {expected!r}."
            )
            return self
        raise AssertionError("contains requires an iterable value.")

    def has_length(self, expected_length: int) -> "AssertionBuilder":
        if isinstance(self.actual, (Sequence, Mapping, set, frozenset)):
            assert len(self.actual) == expected_length, (
                f"Expected length {expected_length} but received {len(self.actual)}."
            )
            return self
        raise AssertionError("has_length requires a sized collection.")


def assert_that(actual: T) -> AssertionBuilder:
    """Return a fluent assertion builder for the provided value."""

    return AssertionBuilder(actual)
