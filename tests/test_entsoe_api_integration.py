import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "custom_components"))
sys.path.insert(0, str(project_root / "custom_components" / "entsoe_qh"))

from shared.api import EntsoeApiClient, PricePoint
from shared.constants import DEFAULT_CURRENCY, DEFAULT_DOMAIN, DEFAULT_ENERGY_UNIT
from shared.models import SeriesData

@pytest.mark.integration
def test_entsoe_api_client_real_api_returns_prices():
    security_token = os.getenv("ENTSOE_API_KEY")
    if security_token is None or security_token.strip() == "":
        pytest.skip("Missing ENTSOE_API_KEY environment variable")

    client = EntsoeApiClient(
        session=None,
        security_token=security_token,
        domain=DEFAULT_DOMAIN,
        currency=DEFAULT_CURRENCY,
        energy_unit=DEFAULT_ENERGY_UNIT,
        vat=0.0,
        currency_rate=1.0,
    )

    data = asyncio.run(client.get_converted_prices())

    assert "quarter_hour" in data
    assert "hour" in data

    quarter_series = data["quarter_hour"]
    hour_series = data["hour"]

    assert isinstance(quarter_series, SeriesData)
    assert isinstance(hour_series, SeriesData)

    assert quarter_series.unit == f"{DEFAULT_CURRENCY}/{DEFAULT_ENERGY_UNIT}"
    assert quarter_series.currency == DEFAULT_CURRENCY
    assert isinstance(quarter_series.updated_at, datetime)
    assert quarter_series.updated_at.tzinfo is not None
    assert isinstance(quarter_series.start, datetime)
    assert quarter_series.start.tzinfo is not None
    assert quarter_series.step_minutes in (15, 30, 60)
    assert isinstance(quarter_series.today, tuple)
    assert len(quarter_series.today) > 0
    assert len(quarter_series.today) <= 96
    if quarter_series.tomorrow is not None:
        assert isinstance(quarter_series.tomorrow, tuple)
        assert len(quarter_series.tomorrow) <= 96

    assert hour_series.step_minutes == 60
    assert len(hour_series.today) <= 24
    assert hour_series.updated_at == quarter_series.updated_at

    attributes = quarter_series.as_attributes()
    assert "today" in attributes
    assert isinstance(attributes["today"], list)
    assert attributes["unit_of_measurement"] == quarter_series.unit
    assert "updated_at" in attributes


def test_compact_series_attributes(monkeypatch: pytest.MonkeyPatch):
    client = EntsoeApiClient(
        session=None,
        security_token="token",
        domain=DEFAULT_DOMAIN,
        currency=DEFAULT_CURRENCY,
        energy_unit=DEFAULT_ENERGY_UNIT,
        vat=0.0,
        currency_rate=1.0,
    )

    base = datetime(2025, 1, 2, tzinfo=timezone.utc)
    price_points: list[PricePoint] = []
    for day in range(2):
        day_start = base + timedelta(days=day)
        for slot in range(96):
            timestamp = day_start + timedelta(minutes=15 * slot)
            value = Decimal("50") + (Decimal(slot) / Decimal("1000"))
            price_points.append(PricePoint(timestamp=timestamp, price_eur_mwh=value))

    async def fake_fetch(*args: Any, **kwargs: Any) -> str:
        return ""

    monkeypatch.setattr(client, "_fetch_prices_xml", fake_fetch)
    monkeypatch.setattr(client, "_parse_prices", lambda *_: price_points)

    data = asyncio.run(client.get_converted_prices(now=base))
    quarter_series = data["quarter_hour"]
    hour_series = data["hour"]

    attrs = quarter_series.as_attributes()
    assert len(json.dumps(attrs)) < 8192
    assert len(attrs["today"]) <= 96
    if "tomorrow" in attrs:
        assert len(attrs["tomorrow"]) <= 96
    assert quarter_series.step_minutes == 15
    assert hour_series.step_minutes == 60
    assert len(hour_series.today) <= 24

    forbidden_fragments = ("raw", "series", "points", "time", "timestamp")
    for key in attrs.keys():
        for fragment in forbidden_fragments:
            assert fragment not in key

    assert attrs["today_min"] is not None
    assert attrs["today_max"] is not None
    assert attrs["today_avg"] is not None
    if "tomorrow" in attrs:
        assert attrs["tomorrow_min"] is not None
        assert attrs["tomorrow_max"] is not None
        assert attrs["tomorrow_avg"] is not None

    assert all(abs(value - round(value, 4)) < 1e-9 for value in attrs["today"])
    if "tomorrow" in attrs:
        assert all(abs(value - round(value, 4)) < 1e-9 for value in attrs["tomorrow"])
