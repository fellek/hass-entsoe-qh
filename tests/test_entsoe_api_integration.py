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
    ATTR_PRICES_TODAY,
    ATTR_PRICES_TOMORROW,
    ATTR_PRICE_FIELDS,
    ATTR_RAW_PRICE,
    ATTR_UPDATED_AT,
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

    prices = data["prices"]
    assert isinstance(prices, list)
    assert len(prices) > 0

    first_point = prices[0]
    assert isinstance(first_point, list)
    assert len(first_point) == 3
    timestamp_value, converted_value, raw_value = first_point
    assert isinstance(timestamp_value, int)
    assert isinstance(converted_value, float)
    assert isinstance(raw_value, float)

    today_prices = data[ATTR_PRICES_TODAY]
    assert isinstance(today_prices, list)
    assert len(today_prices) > 0

    today_timestamps = {item[0] for item in today_prices}
    price_timestamps = {item[0] for item in prices}
    assert today_timestamps.issubset(price_timestamps)

    assert ATTR_PRICES_TOMORROW in data
    tomorrow_prices = data[ATTR_PRICES_TOMORROW]
    assert isinstance(tomorrow_prices, list)

    fields = data[ATTR_PRICE_FIELDS]
    assert isinstance(fields, list)
    assert fields == ["timestamp", "value", ATTR_RAW_PRICE]

    current_price = data["current_price"]
    assert current_price is None or isinstance(current_price, float)

    hour_price = data["hour_price"]
    assert hour_price is None or isinstance(hour_price, float)
