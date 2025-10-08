from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import logging
from typing import Any
import xml.etree.ElementTree as ET

from aiohttp import ClientError, ClientSession

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_PRICES_TODAY,
    ATTR_PRICES_TOMORROW,
    ATTR_RAW_PRICE,
    ATTR_UPDATED_AT,
    ENTSOE_API_URL,
    REQUEST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class PricePoint:
    timestamp: datetime
    price_eur_mwh: Decimal


class EntsoeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        session: ClientSession,
        security_token: str,
        in_domain: str,
        out_domain: str,
        currency: str,
        energy_unit: str,
        vat: float,
        currency_rate: float,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="ENTSO-E Quarter-Hour",
            update_interval=update_interval,
        )
        self.session = session
        self.security_token = security_token
        self.in_domain = in_domain
        self.out_domain = out_domain
        self.currency = currency
        self.energy_unit = energy_unit
        self.vat = vat
        self.currency_rate = currency_rate if currency_rate > 0 else 1.0

    async def _async_update_data(self) -> dict[str, Any]:
        start, end = self._period_range()
        params = {
            "securityToken": self.security_token,
            "documentType": "A44",
            "in_Domain": self.in_domain,
            "out_Domain": self.out_domain,
            "periodStart": start,
            "periodEnd": end,
        }

        try:
            async with self.session.get(
                ENTSOE_API_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            ) as response:
                text = await response.text()
        except ClientError as err:
            raise UpdateFailed(f"Błąd komunikacji z ENTSO-E: {err}") from err

        if response.status != 200:
            raise UpdateFailed(
                f"Błąd pobierania danych ENTSO-E: {response.status} - {text}"
            )

        prices = self._parse_prices(text)
        if not prices:
            raise UpdateFailed("Brak danych cenowych z ENTSO-E")

        converted = self._convert_prices(prices)
        return converted

    def _period_range(self) -> tuple[str, str]:
        now = dt_util.utcnow()
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(days=2)
        return start_dt.strftime("%Y%m%d%H%M"), end_dt.strftime("%Y%m%d%H%M")

    def _parse_prices(self, xml_text: str) -> list[PricePoint]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as err:
            raise UpdateFailed(f"Nieprawidłowa odpowiedź XML: {err}") from err

        namespace = {
            "ns": "urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0"
        }
        points: list[PricePoint] = []

        for series in root.findall(".//ns:TimeSeries", namespace):
            for period in series.findall("ns:Period", namespace):
                start_text = period.findtext("ns:timeInterval/ns:start", namespaces=namespace)
                resolution = period.findtext("ns:resolution", namespaces=namespace)
                if start_text is None or resolution != "PT15M":
                    continue
                start_time = dt_util.parse_datetime(start_text)
                if start_time is None:
                    continue
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=dt_util.UTC)
                for point in period.findall("ns:Point", namespace):
                    position_text = point.findtext("ns:position", namespaces=namespace)
                    price_text = point.findtext("ns:price.amount", namespaces=namespace)
                    if position_text is None or price_text is None:
                        continue
                    try:
                        position = int(position_text)
                        price = Decimal(price_text)
                    except (ValueError, InvalidOperation):
                        continue
                    timestamp = start_time + timedelta(minutes=15 * (position - 1))
                    points.append(PricePoint(timestamp=timestamp, price_eur_mwh=price))

        points.sort(key=lambda item: item.timestamp)
        return points

    def _convert_prices(self, prices: list[PricePoint]) -> dict[str, Any]:
        now = dt_util.utcnow().replace(second=0, microsecond=0)
        conversion_rate = Decimal(str(self.currency_rate))
        vat_multiplier = Decimal("1") + (Decimal(str(self.vat)) / Decimal("100"))
        energy_divisor = Decimal("1")
        if self.energy_unit == "kWh":
            energy_divisor = Decimal("1000")

        converted_points: list[dict[str, Any]] = []
        today_points: list[dict[str, Any]] = []
        tomorrow_points: list[dict[str, Any]] = []

        for point in prices:
            converted_value = (point.price_eur_mwh / energy_divisor) * conversion_rate
            converted_value *= vat_multiplier
            converted_value = converted_value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            data = {
                "timestamp": point.timestamp,
                "value": float(converted_value),
                ATTR_RAW_PRICE: float(point.price_eur_mwh),
            }
            converted_points.append(data)
            if point.timestamp.date() == now.date():
                today_points.append(data)
            elif point.timestamp.date() == (now + timedelta(days=1)).date():
                tomorrow_points.append(data)

        price_map = {item["timestamp"]: item["value"] for item in converted_points}

        current_slot = now.replace(minute=(now.minute // 15) * 15)
        current_price = price_map.get(current_slot)
        if current_price is None:
            future_points = [item for item in converted_points if item["timestamp"] >= now]
            if future_points:
                current_price = future_points[0]["value"]

        hour_start = now.replace(minute=0)
        hour_slots = [hour_start + timedelta(minutes=15 * idx) for idx in range(4)]
        hour_values = [price_map.get(slot) for slot in hour_slots if price_map.get(slot) is not None]
        hour_price = sum(hour_values) / len(hour_values) if hour_values else current_price

        unit = f"{self.currency}/{self.energy_unit}"

        return {
            "unit": unit,
            "current_price": current_price,
            "hour_price": hour_price,
            "prices": converted_points,
            ATTR_PRICES_TODAY: today_points,
            ATTR_PRICES_TOMORROW: tomorrow_points,
            ATTR_UPDATED_AT: dt_util.utcnow().isoformat(),
        }
