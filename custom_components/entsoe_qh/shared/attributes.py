"""Helpers for preparing attribute payloads exposed by sensors."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .constants import (
    ATTR_DURATION_MINUTES,
    ATTR_PRICE_ID,
    ATTR_PRICE_START,
    ATTR_RAW_PRICE,
    ATTR_SERIES_TOTAL_POINTS,
    ATTR_SERIES_TRUNCATED,
    ATTR_VALUE,
)

MAX_SERIES_POINTS = 10


def compact_series_attributes(
    series: dict[str, Any] | None,
    *,
    max_points: int = MAX_SERIES_POINTS,
) -> dict[str, Any]:
    """Return a compact representation of price series metadata."""

    if not isinstance(series, dict) or max_points <= 0:
        return {}

    values = _ensure_list(series.get(ATTR_VALUE))
    total_points = len(values)
    limit = min(max_points, total_points)

    if total_points == 0:
        return {
            ATTR_DURATION_MINUTES: series.get(ATTR_DURATION_MINUTES),
            ATTR_SERIES_TOTAL_POINTS: 0,
        }

    price_ids = _ensure_list(series.get(ATTR_PRICE_ID))[:limit]
    starts = _ensure_list(series.get(ATTR_PRICE_START))[:limit]
    raw_prices = _ensure_list(series.get(ATTR_RAW_PRICE))[:limit]

    compacted = {
        ATTR_DURATION_MINUTES: series.get(ATTR_DURATION_MINUTES),
        ATTR_PRICE_ID: price_ids,
        ATTR_PRICE_START: [_format_start(item) for item in starts],
        ATTR_VALUE: values[:limit],
        ATTR_RAW_PRICE: raw_prices,
        ATTR_SERIES_TOTAL_POINTS: total_points,
    }

    if total_points > limit:
        compacted[ATTR_SERIES_TRUNCATED] = True

    return compacted


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
