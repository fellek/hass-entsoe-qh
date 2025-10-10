from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass
class ShouldWrapper:
    actual: Any

    def be(self, expected: Any) -> None:
        assert self.actual == expected, (
            f"Oczekiwano wartości {expected!r}, otrzymano {self.actual!r}."
        )

    def be_true(self) -> None:
        assert bool(self.actual) is True, (
            f"Oczekiwano wartości prawdziwej, otrzymano {self.actual!r}."
        )

    def not_be_empty(self) -> None:
        if isinstance(self.actual, Iterable):
            assert any(True for _ in self.actual), "Oczekiwano niepustej kolekcji."
            return
        raise AssertionError("Metoda not_be_empty wymaga kolekcji.")


def should(actual: Any) -> ShouldWrapper:
    return ShouldWrapper(actual)
