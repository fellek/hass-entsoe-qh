from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

try:  # pragma: no cover - opcjonalne importowanie dla środowiska Home Assistant
    from aiohttp import ClientError, ClientSession
except ModuleNotFoundError:  # pragma: no cover - fallback dla środowisk bez aiohttp
    ClientSession = None  # type: ignore

    class ClientError(Exception):
        """Awaryjna definicja błędu klienta HTTP."""

from entsoe_qh_shared.constants import (
    ATTR_PRICES_TODAY,
    ATTR_PRICES_TOMORROW,
    ATTR_RAW_PRICE,
    ATTR_UPDATED_AT,
    ENTSOE_API_URL,
    REQUEST_TIMEOUT,
)


class EntsoeApiError(Exception):
    """Wyjątek sygnalizujący błąd podczas komunikacji z ENTSO-E."""


@dataclass
class PricePoint:
    timestamp: datetime
    price_eur_mwh: Decimal


class EntsoeApiClient:
    ENTSOE_TIMEZONE = ZoneInfo("Europe/Brussels")

    def __init__(
        self,
        session: ClientSession | None,
        security_token: str,
        in_domain: str,
        out_domain: str,
        currency: str,
        energy_unit: str,
        vat: float,
        currency_rate: float,
    ) -> None:
        self.session = session
        self.security_token = security_token
        self.in_domain = in_domain
        self.out_domain = out_domain
        self.currency = currency
        self.energy_unit = energy_unit
        self.vat = vat
        self.currency_rate = currency_rate if currency_rate > 0 else 1.0

    async def get_converted_prices(self, now: datetime | None = None) -> dict[str, Any]:
        start, end = self._period_range(now)
        xml_text = await self._fetch_prices_xml(start, end)
        prices = self._parse_prices(xml_text)
        if not prices:
            raise EntsoeApiError("Brak danych cenowych z ENTSO-E")
        return self._convert_prices(prices, now)

    async def _fetch_prices_xml(self, start: str, end: str) -> str:
        params = {
            "securityToken": self.security_token,
            "documentType": "A44",
            "in_Domain": self.in_domain,
            "out_Domain": self.out_domain,
            "periodStart": start,
            "periodEnd": end,
        }

        if self.session is not None:
            try:
                async with self.session.get(
                    ENTSOE_API_URL,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                ) as response:
                    text = await response.text()
                    status = response.status
            except ClientError as err:
                raise EntsoeApiError(f"Błąd komunikacji z ENTSO-E: {err}") from err
        else:
            text, status = await self._fetch_with_stdlib(params)

        if status != 200:
            raise EntsoeApiError(
                f"Błąd pobierania danych ENTSO-E: {status} - {text}"
            )

        return text

    def _period_range(self, now: datetime | None) -> tuple[str, str]:
        current = self._ensure_utc(now).astimezone(self.ENTSOE_TIMEZONE)
        start_dt = current.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(days=2)
        return start_dt.strftime("%Y%m%d%H%M"), end_dt.strftime("%Y%m%d%H%M")

    async def _fetch_with_stdlib(self, params: dict[str, Any]) -> tuple[str, int]:
        url = f"{ENTSOE_API_URL}?{urlencode(params)}"

        def _request() -> tuple[str, int]:
            request = Request(url)
            with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                status_code = response.getcode()
                payload = response.read().decode()
            return payload, status_code

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _request)

    def _parse_prices(self, xml_text: str) -> list[PricePoint]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as err:
            raise EntsoeApiError(f"Nieprawidłowa odpowiedź XML: {err}") from err

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
                start_time = self._parse_datetime(start_text)
                if start_time is None:
                    continue
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

    def _convert_prices(
        self,
        prices: list[PricePoint],
        now: datetime | None,
    ) -> dict[str, Any]:
        current_time = self._ensure_utc(now).replace(second=0, microsecond=0)
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
            if point.timestamp.date() == current_time.date():
                today_points.append(data)
            elif point.timestamp.date() == (current_time + timedelta(days=1)).date():
                tomorrow_points.append(data)

        price_map = {item["timestamp"]: item["value"] for item in converted_points}

        current_slot = current_time.replace(minute=(current_time.minute // 15) * 15)
        current_price = price_map.get(current_slot)
        if current_price is None:
            future_points = [item for item in converted_points if item["timestamp"] >= current_time]
            if future_points:
                current_price = future_points[0]["value"]

        hour_start = current_time.replace(minute=0)
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
            ATTR_UPDATED_AT: datetime.now(timezone.utc).isoformat(),
        }

    def _ensure_utc(self, value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
