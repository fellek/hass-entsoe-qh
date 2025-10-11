from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

import pytest

from custom_components.entsoe_qh.shared.api import EntsoeApiClient
from custom_components.entsoe_qh.shared.constants import (
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
    DEFAULT_ENERGY_UNIT,
    ENTSOE_DOMAIN_CHOICES,
    ENTSOE_DOMAIN_EXPECTED_RESOLUTIONS,
)
from tests.assertions import assert_that


TOKEN_ENVIRONMENT_VARIABLE = "ENTSOE_API_KEY"
RESOLUTION_BY_SERIES = {
    "quarter_hour": 15,
    "half_hour": 30,
    "hour": 60,
}


@pytest.mark.integration
@pytest.mark.parametrize("country_name, domain", ENTSOE_DOMAIN_CHOICES)
def test_entsoe_api_returns_expected_series(country_name: str, domain: str) -> None:
    token = os.getenv(TOKEN_ENVIRONMENT_VARIABLE, "").strip()
    if not token:
        pytest.skip(
            f"Set the {TOKEN_ENVIRONMENT_VARIABLE} environment variable to run live ENTSO-E tests."
        )

    expected_resolutions = ENTSOE_DOMAIN_EXPECTED_RESOLUTIONS.get(domain)
    assert_that(expected_resolutions is not None).is_true()
    assert_that(expected_resolutions).is_not_empty()

    # Arrange
    client = EntsoeApiClient(
        session=None,
        security_token=token,
        domain=domain,
        currency=DEFAULT_CURRENCY,
        energy_unit=DEFAULT_ENERGY_UNIT,
        vat=0,
        currency_rate=1,
    )
    now = datetime.now(timezone.utc)

    # Act
    data = asyncio.run(client.get_converted_prices(now))

    # Assert
    assert_that(data).contains("unit")
    assert_that(data).contains(ATTR_SERIES)
    assert_that(data[ATTR_SERIES]).is_instance_of(dict)
    assert_that(data).contains(ATTR_PRICE_FIELDS)
    assert_that(data[ATTR_PRICE_FIELDS]).contains(ATTR_PRICE_ID)
    assert_that(data[ATTR_PRICE_FIELDS]).contains(ATTR_PRICE_START)
    assert_that(data[ATTR_PRICE_FIELDS]).contains(ATTR_VALUE)
    assert_that(data[ATTR_PRICE_FIELDS]).contains(ATTR_RAW_PRICE)
    assert_that(data).contains(ATTR_UPDATED_AT)

    series = data[ATTR_SERIES]
    actual_resolutions: set[int] = set()

    for series_name, minutes in RESOLUTION_BY_SERIES.items():
        if series_name not in series:
            continue
        entry = series[series_name]
        today = entry[ATTR_PRICES_TODAY]
        tomorrow = entry[ATTR_PRICES_TOMORROW]

        assert_that(today).contains(ATTR_PRICE_ID)
        assert_that(today).contains(ATTR_PRICE_START)
        assert_that(today).contains(ATTR_VALUE)
        assert_that(today).contains(ATTR_RAW_PRICE)
        assert_that(tomorrow).contains(ATTR_PRICE_ID)
        assert_that(tomorrow).contains(ATTR_PRICE_START)
        assert_that(tomorrow).contains(ATTR_VALUE)
        assert_that(tomorrow).contains(ATTR_RAW_PRICE)

        has_today_prices = bool(today[ATTR_PRICE_ID])
        has_tomorrow_prices = bool(tomorrow[ATTR_PRICE_ID])
        assert_that(has_today_prices or has_tomorrow_prices).is_true()

        actual_resolutions.add(minutes)

    expected_set = set(expected_resolutions)
    assert_that(actual_resolutions.issuperset(expected_set)).is_true()
