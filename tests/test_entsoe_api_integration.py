from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

import pytest

from custom_components.entsoe_qh.shared.api import EntsoeApiClient, EntsoeApiError
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
from tests.assertions import assert_that


SAMPLE_XML = """
<Publication_MarketDocument xmlns="urn:entsoe.eu:wgedi:schema">
  <TimeSeries>
    <Period>
      <timeInterval>
        <start>2024-01-01T00:00Z</start>
        <end>2024-01-01T01:00Z</end>
      </timeInterval>
      <resolution>PT15M</resolution>
      <Point>
        <position>1</position>
        <price.amount>100</price.amount>
      </Point>
      <Point>
        <position>2</position>
        <price.amount>200</price.amount>
      </Point>
      <Point>
        <position>3</position>
        <price.amount>300</price.amount>
      </Point>
      <Point>
        <position>4</position>
        <price.amount>400</price.amount>
      </Point>
    </Period>
    <Period>
      <timeInterval>
        <start>2024-01-02T00:00Z</start>
        <end>2024-01-02T01:00Z</end>
      </timeInterval>
      <resolution>PT15M</resolution>
      <Point>
        <position>1</position>
        <price.amount>500</price.amount>
      </Point>
      <Point>
        <position>2</position>
        <price.amount>600</price.amount>
      </Point>
      <Point>
        <position>3</position>
        <price.amount>700</price.amount>
      </Point>
      <Point>
        <position>4</position>
        <price.amount>800</price.amount>
      </Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>
""".strip()


def _expected_value(price: int, rate: Decimal, vat: Decimal) -> float:
    value = (Decimal(price) / Decimal("1000")) * rate
    value *= (Decimal("1") + vat / Decimal("100"))
    value = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return float(value)


def _expected_hour_value(prices: tuple[int, ...], rate: Decimal, vat: Decimal) -> float:
    converted = [
        (Decimal(price) / Decimal("1000")) * rate * (Decimal("1") + vat / Decimal("100"))
        for price in prices
    ]
    quantized = [item.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) for item in converted]
    average = (sum(quantized, Decimal("0")) / Decimal(len(quantized))).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    return float(average)


def _expected_hour_current(prices: tuple[int, ...], rate: Decimal, vat: Decimal) -> float:
    converted = [
        (Decimal(price) / Decimal("1000")) * rate * (Decimal("1") + vat / Decimal("100"))
        for price in prices
    ]
    quantized = [item.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) for item in converted]
    average = (sum(quantized, Decimal("0")) / Decimal(len(quantized))).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    return float(average)


def test_get_converted_prices_returns_expected_structure(monkeypatch):
    # Arrange
    captured: dict[str, str] = {}

    async def fake_fetch(self: EntsoeApiClient, start: str, end: str) -> str:
        captured["start"] = start
        captured["end"] = end
        return SAMPLE_XML

    monkeypatch.setattr(EntsoeApiClient, "_fetch_prices_xml", fake_fetch)
    monkeypatch.setattr(EntsoeApiClient, "ENTSOE_TIMEZONE", None)

    vat = Decimal("21")
    rate = Decimal("0.5")
    client = EntsoeApiClient(
        session=None,
        security_token="token",
        domain=DEFAULT_DOMAIN,
        currency=DEFAULT_CURRENCY,
        energy_unit=DEFAULT_ENERGY_UNIT,
        vat=float(vat),
        currency_rate=float(rate),
    )

    now = datetime(2024, 1, 1, 0, 30, tzinfo=timezone.utc)

    # Act
    data = asyncio.run(client.get_converted_prices(now))

    # Assert
    assert_that(captured["start"]).is_equal_to("202401010000")
    assert_that(captured["end"]).is_equal_to("202401030000")
    assert_that(data["unit"]).is_equal_to(f"{DEFAULT_CURRENCY}/{DEFAULT_ENERGY_UNIT}")
    assert_that(data).contains(ATTR_UPDATED_AT)

    series = data[ATTR_SERIES]
    assert_that(series).is_instance_of(dict)
    assert_that(series).contains("quarter_hour")
    assert_that(series).contains("hour")
    assert_that(series).has_length(2)

    quarter_series = series["quarter_hour"]
    assert_that(quarter_series).is_instance_of(dict)
    today_prices = quarter_series[ATTR_PRICES_TODAY]
    tomorrow_prices = quarter_series[ATTR_PRICES_TOMORROW]
    assert_that(today_prices[ATTR_DURATION_MINUTES]).is_equal_to(15)
    assert_that(tomorrow_prices[ATTR_DURATION_MINUTES]).is_equal_to(15)

    expected_today = [
        _expected_value(item, rate, vat) for item in (100, 200, 300, 400)
    ]
    expected_tomorrow = [
        _expected_value(item, rate, vat) for item in (500, 600, 700, 800)
    ]

    assert_that(today_prices[ATTR_VALUE]).is_equal_to(expected_today)
    assert_that(tomorrow_prices[ATTR_VALUE]).is_equal_to(expected_tomorrow)
    assert_that(today_prices[ATTR_PRICE_START][0]).is_equal_to("2024-01-01T00:00:00+00:00")
    assert_that(tomorrow_prices[ATTR_PRICE_START][0]).is_equal_to("2024-01-02T00:00:00+00:00")
    assert_that(today_prices[ATTR_PRICE_ID]).has_length(4)
    assert_that(tomorrow_prices[ATTR_PRICE_ID]).has_length(4)

    hour_series = series["hour"]
    assert_that(hour_series).is_instance_of(dict)
    assert_that(hour_series[ATTR_PRICES_TODAY][ATTR_VALUE]).is_equal_to([
        _expected_hour_value((100, 200, 300, 400), rate, vat)
    ])
    assert_that(hour_series[ATTR_PRICES_TOMORROW][ATTR_VALUE]).is_equal_to([
        _expected_hour_value((500, 600, 700, 800), rate, vat)
    ])
    assert_that(hour_series["current"]).is_equal_to(
        _expected_hour_current((100, 200, 300, 400), rate, vat)
    )
    assert_that(quarter_series["current"]).is_equal_to(expected_today[2])

    assert_that("half_hour" in series).is_false()

    fields = data[ATTR_PRICE_FIELDS]
    assert_that(fields).is_equal_to([
        ATTR_PRICE_ID,
        ATTR_PRICE_START,
        ATTR_VALUE,
        ATTR_RAW_PRICE,
    ])


SAMPLE_HOURLY_XML = """
<Publication_MarketDocument xmlns="urn:entsoe.eu:wgedi:schema">
  <TimeSeries>
    <Period>
      <timeInterval>
        <start>2024-01-01T00:00Z</start>
        <end>2024-01-01T02:00Z</end>
      </timeInterval>
      <resolution>PT60M</resolution>
      <Point>
        <position>1</position>
        <price.amount>120</price.amount>
      </Point>
      <Point>
        <position>2</position>
        <price.amount>180</price.amount>
      </Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>
""".strip()


def test_get_converted_prices_with_hourly_resolution_returns_only_hour_series(monkeypatch):
    # Arrange
    async def fake_fetch(self: EntsoeApiClient, start: str, end: str) -> str:  # noqa: ARG001
        return SAMPLE_HOURLY_XML

    monkeypatch.setattr(EntsoeApiClient, "_fetch_prices_xml", fake_fetch)
    monkeypatch.setattr(EntsoeApiClient, "ENTSOE_TIMEZONE", None)

    client = EntsoeApiClient(
        session=None,
        security_token="token",
        domain=DEFAULT_DOMAIN,
        currency=DEFAULT_CURRENCY,
        energy_unit=DEFAULT_ENERGY_UNIT,
        vat=0.0,
        currency_rate=1.0,
    )

    now = datetime(2024, 1, 1, 0, 30, tzinfo=timezone.utc)

    # Act
    data = asyncio.run(client.get_converted_prices(now))

    # Assert
    series = data[ATTR_SERIES]
    assert_that(series).contains("hour")
    assert_that(series).has_length(1)
    assert_that("quarter_hour" in series).is_false()
    assert_that("half_hour" in series).is_false()

    hour_series = series["hour"]
    today_values = hour_series[ATTR_PRICES_TODAY][ATTR_VALUE]
    assert_that(today_values).is_equal_to([0.12, 0.18])
    assert_that(hour_series["current"]).is_equal_to(0.12)


def test_get_converted_prices_without_values_raises(monkeypatch):
    # Arrange
    async def fake_fetch(self: EntsoeApiClient, start: str, end: str) -> str:  # noqa: ARG001
        return "<Publication_MarketDocument></Publication_MarketDocument>"

    monkeypatch.setattr(EntsoeApiClient, "_fetch_prices_xml", fake_fetch)
    monkeypatch.setattr(EntsoeApiClient, "ENTSOE_TIMEZONE", None)

    client = EntsoeApiClient(
        session=None,
        security_token="token",
        domain=DEFAULT_DOMAIN,
        currency=DEFAULT_CURRENCY,
        energy_unit=DEFAULT_ENERGY_UNIT,
        vat=0.0,
        currency_rate=1.0,
    )

    # Act
    with pytest.raises(EntsoeApiError) as err:
        asyncio.run(client.get_converted_prices(datetime(2024, 1, 1, tzinfo=timezone.utc)))

    # Assert
    assert_that(str(err.value)).is_equal_to("No price data available from ENTSO-E")
