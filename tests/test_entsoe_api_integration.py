from __future__ import annotations

import asyncio
import os

import pytest

from custom_components.entsoe_qh.shared.api import EntsoeApiClient
from custom_components.entsoe_qh.shared.constants import (
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
from assertpy import assert_that


TOKEN_ENVIRONMENT_VARIABLE = "ENTSOE_API_KEY"


@pytest.mark.integration
def test_entsoe_api_client_real_api_returns_prices() -> None:
    token = os.getenv(TOKEN_ENVIRONMENT_VARIABLE, "").strip()
    if not token:
        pytest.skip(
            f"Set the {TOKEN_ENVIRONMENT_VARIABLE} environment variable to run live ENTSO-E integration tests."
        )

    # Arrange
    client = EntsoeApiClient(
        session=None,
        security_token=token,
        domain=DEFAULT_DOMAIN,
        currency=DEFAULT_CURRENCY,
        energy_unit=DEFAULT_ENERGY_UNIT,
        vat=0.0,
        currency_rate=1.0,
    )

    # Act
    data = asyncio.run(client.get_converted_prices())

    # Assert
    assert_that(data["unit"]).is_equal_to(f"{DEFAULT_CURRENCY}/{DEFAULT_ENERGY_UNIT}")
    assert_that(data).contains(ATTR_UPDATED_AT)
    assert_that(data).contains(ATTR_SERIES)
    assert_that(data[ATTR_SERIES]).is_instance_of(dict)
    assert_that(data).contains(ATTR_PRICE_FIELDS)
    assert_that(data[ATTR_PRICE_FIELDS]).is_equal_to(
        [ATTR_PRICE_ID, ATTR_PRICE_START, ATTR_VALUE, ATTR_RAW_PRICE]
    )

    series = data[ATTR_SERIES]
    assert_that("hour" in series).is_true()

    hour_series = series["hour"]
    current_hour = hour_series.get("current")
    assert_that(current_hour is None or isinstance(current_hour, float)).is_true()

    today_hour = hour_series[ATTR_PRICES_TODAY]
    assert_that(today_hour[ATTR_DURATION_MINUTES]).is_equal_to(60)
    assert_that(today_hour[ATTR_PRICE_ID]).is_not_empty()
    assert_that(today_hour[ATTR_PRICE_START]).is_not_empty()
    assert_that(today_hour[ATTR_VALUE]).is_not_empty()

    quarter_series = series.get("quarter_hour")
    if quarter_series is not None:
        current_quarter = quarter_series.get("current")
        assert_that(current_quarter is None or isinstance(current_quarter, float)).is_true()

        today_quarter = quarter_series[ATTR_PRICES_TODAY]
        assert_that(today_quarter[ATTR_DURATION_MINUTES]).is_equal_to(15)
        assert_that(today_quarter[ATTR_VALUE]).is_not_empty()

        tomorrow_quarter = quarter_series[ATTR_PRICES_TOMORROW]
        assert_that(tomorrow_quarter[ATTR_DURATION_MINUTES]).is_equal_to(15)

    tomorrow_hour = hour_series[ATTR_PRICES_TOMORROW]
    assert_that(tomorrow_hour[ATTR_DURATION_MINUTES]).is_equal_to(60)
    assert_that(tomorrow_hour[ATTR_PRICE_ID]).is_instance_of(list)
    assert_that(tomorrow_hour[ATTR_PRICE_START]).is_instance_of(list)
    assert_that(tomorrow_hour[ATTR_VALUE]).is_instance_of(list)
