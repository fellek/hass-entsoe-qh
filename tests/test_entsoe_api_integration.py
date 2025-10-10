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
    ATTR_CURRENT,
    ATTR_CURRENCY,
    ATTR_SERIES,
    ATTR_SOURCE,
    ATTR_START,
    ATTR_STEP_MINUTES,
    ATTR_TODAY,
    ATTR_TODAY_AVG,
    ATTR_TODAY_MAX,
    ATTR_TODAY_MIN,
    ATTR_TOMORROW,
    ATTR_UPDATED_AT,
    ATTR_UNIT,
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

    assert data[ATTR_UNIT] == f"{DEFAULT_CURRENCY}/{DEFAULT_ENERGY_UNIT}"
    assert ATTR_UPDATED_AT in data
    assert data[ATTR_CURRENCY] == DEFAULT_CURRENCY
    assert data[ATTR_SOURCE] == "ENTSO-E"

    series = data[ATTR_SERIES]
    assert isinstance(series, dict)

    assert "quarter_hour" in series
    quarter_series = series["quarter_hour"]
    assert isinstance(quarter_series, dict)

    current_quarter = quarter_series.get(ATTR_CURRENT)
    assert current_quarter is None or isinstance(current_quarter, float)

    today_prices = quarter_series[ATTR_TODAY]
    assert isinstance(today_prices, list)
    assert len(today_prices) > 0
    assert ATTR_TODAY_MIN in quarter_series
    assert ATTR_TODAY_MAX in quarter_series
    assert ATTR_TODAY_AVG in quarter_series

    if ATTR_TOMORROW in quarter_series:
        tomorrow_prices = quarter_series[ATTR_TOMORROW]
        assert isinstance(tomorrow_prices, list)

    assert quarter_series[ATTR_STEP_MINUTES] in {15, 30, 60}
    assert quarter_series[ATTR_START].endswith(":00")

    assert "hour" in series
    hour_series = series["hour"]
    assert isinstance(hour_series, dict)
    current_hour = hour_series.get(ATTR_CURRENT)
    assert current_hour is None or isinstance(current_hour, float)
    assert isinstance(hour_series[ATTR_TODAY], list)
    assert hour_series[ATTR_STEP_MINUTES] == 60
