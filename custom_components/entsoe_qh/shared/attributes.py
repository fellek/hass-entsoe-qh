"""Helpers for preparing attribute payloads exposed by sensors."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .constants import (
    ATTR_DURATION_MINUTES,
    ATTR_PRICE_START,
    ATTR_RAW_PRICE,
    ATTR_SERIES_TOTAL_POINTS,
)

# Safety cap only. A local day has at most 100 quarter hours (DST end), so the
# cap never applies in normal operation and keeps the payload well below the
# recorder's 16 KB attribute limit.
MAX_SERIES_POINTS = 200


def compact_series_attributes(
    series: dict[str, Any] | None,
    *,
    max_points: int = MAX_SERIES_POINTS,
) -> dict[str, Any]:
    """Return the start times and raw prices of a price series."""

    if not isinstance(series, dict) or max_points <= 0:
        return {}

    starts = _ensure_list(series.get(ATTR_PRICE_START))
    raw_prices = _ensure_list(series.get(ATTR_RAW_PRICE))
    limit = min(len(starts), len(raw_prices), max_points)

    if limit == 0:
        return {
            ATTR_DURATION_MINUTES: series.get(ATTR_DURATION_MINUTES),
            ATTR_SERIES_TOTAL_POINTS: 0,
        }

    return {
        ATTR_DURATION_MINUTES: series.get(ATTR_DURATION_MINUTES),
        ATTR_PRICE_START: [_format_start(item) for item in starts[:limit]],
        ATTR_RAW_PRICE: raw_prices[:limit],
        ATTR_SERIES_TOTAL_POINTS: limit,
    }


def _ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _format_start(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)

    return parsed.strftime("%Y-%m-%dT%H:%MZ")
