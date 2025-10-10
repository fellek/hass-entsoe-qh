from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class SeriesData:
    current: float | None
    start: datetime
    step_minutes: int
    today: tuple[float, ...]
    tomorrow: tuple[float, ...] | None
    today_min: float | None
    today_max: float | None
    today_avg: float | None
    tomorrow_min: float | None
    tomorrow_max: float | None
    tomorrow_avg: float | None
    updated_at: datetime
    currency: str
    unit: str
    in_domain: str
    out_domain: str
    source: str

    def as_attributes(self) -> dict[str, Any]:
        attributes: dict[str, Any] = {
            "unit_of_measurement": self.unit,
            "currency": self.currency,
            "start": self.start.isoformat(),
            "step_minutes": self.step_minutes,
            "today": list(self.today),
            "today_min": self.today_min,
            "today_max": self.today_max,
            "today_avg": self.today_avg,
            "updated_at": self.updated_at.isoformat(),
            "source": self.source,
            "in_domain": self.in_domain,
            "out_domain": self.out_domain,
        }

        if self.tomorrow is not None and len(self.tomorrow) > 0:
            attributes["tomorrow"] = list(self.tomorrow)
            attributes["tomorrow_min"] = self.tomorrow_min
            attributes["tomorrow_max"] = self.tomorrow_max
            attributes["tomorrow_avg"] = self.tomorrow_avg

        return attributes
