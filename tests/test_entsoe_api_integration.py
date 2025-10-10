import asyncio
import os
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "custom_components"))
sys.path.insert(0, str(project_root / "custom_components" / "entsoe_qh"))

from shared.api import EntsoeApiClient
from shared.constants import (
    ATTR_DURATION_MINUTES,
    ATTR_PRICES_TODAY,
    ATTR_PRICES_TOMORROW,
    ATTR_PRICE_FIELDS,
    ATTR_PRICE_ID,
    ATTR_PRICE_START,
    ATTR_RAW_PRICE,
    ATTR_SERIES,
    ATTR_UPDATED_AT,
    ATTR_VALUE,
    DEFAULT_CURRENCY,
    DEFAULT_DOMAIN,
    DEFAULT_ENERGY_UNIT,
)

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

    assert data["unit"] == f"{DEFAULT_CURRENCY}/{DEFAULT_ENERGY_UNIT}"
    assert ATTR_UPDATED_AT in data

    series = data[ATTR_SERIES]
    assert isinstance(series, dict)

    assert "quarter_hour" in series
    quarter_series = series["quarter_hour"]
    assert isinstance(quarter_series, dict)

    current_quarter = quarter_series.get("current")
    assert current_quarter is None or isinstance(current_quarter, float)

    today_prices = quarter_series[ATTR_PRICES_TODAY]
    assert isinstance(today_prices, list)
    assert len(today_prices) > 0

    tomorrow_prices = quarter_series[ATTR_PRICES_TOMORROW]
    assert isinstance(tomorrow_prices, list)

    fields = data[ATTR_PRICE_FIELDS]
    assert isinstance(fields, list)
    assert fields == [
        ATTR_PRICE_ID,
        ATTR_PRICE_START,
        ATTR_DURATION_MINUTES,
        ATTR_VALUE,
        ATTR_RAW_PRICE,
    ]

    first_point = today_prices[0]
    assert isinstance(first_point, dict)
    for field in fields:
        assert field in first_point

    assert isinstance(first_point[ATTR_VALUE], float)
    assert isinstance(first_point[ATTR_RAW_PRICE], float)
    assert isinstance(first_point[ATTR_PRICE_START], str)
    assert isinstance(first_point[ATTR_DURATION_MINUTES], int)

    assert "hour" in series
    hour_series = series["hour"]
    assert isinstance(hour_series, dict)
    current_hour = hour_series.get("current")
    assert current_hour is None or isinstance(current_hour, float)
    assert isinstance(hour_series[ATTR_PRICES_TODAY], list)
