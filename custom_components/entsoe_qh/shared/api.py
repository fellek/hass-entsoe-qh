from __future__ import annotations

import asyncio
import calendar
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:  # pragma: no cover - optional import for the Home Assistant runtime
    from aiohttp import ClientError, ClientSession
except ModuleNotFoundError:  # pragma: no cover - fallback for environments without aiohttp
    ClientSession = None  # type: ignore

    class ClientError(Exception):
        """Fallback definition of an HTTP client error."""

from .constants import (
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
    ENTSOE_API_URL,
    REQUEST_TIMEOUT,
)


_LOGGER = logging.getLogger(__name__)


class EntsoeApiError(Exception):
    """Exception raised when communication with ENTSO-E fails."""


@dataclass
class PricePoint:
    timestamp: datetime
    price_eur_mwh: Decimal
    resolution_minutes: int


@dataclass
class ConvertedPoint:
    start: datetime
    value: Decimal
    raw_value: Decimal
    resolution_minutes: int


class EntsoeApiClient:
    try:
        ENTSOE_TIMEZONE = ZoneInfo("Europe/Brussels")
    except ZoneInfoNotFoundError:
        ENTSOE_TIMEZONE = None

    def __init__(
        self,
        session: ClientSession | None,
        security_token: str,
        domain: str,
        currency: str,
        energy_unit: str,
        vat: float,
        currency_rate: float,
    ) -> None:
        self.session = session
        self.security_token = security_token
        self.domain = domain
        self.currency = currency
        self.energy_unit = energy_unit
        self.vat = vat
        self.currency_rate = currency_rate if currency_rate > 0 else 1.0

    async def get_converted_prices(self, now: datetime | None = None) -> dict[str, Any]:
        start, end = self._period_range(now)
        _LOGGER.info(
            "Starting ENTSO-E data download for the period %s - %s.",
            start,
            end,
        )
        xml_text = await self._fetch_prices_xml(start, end)
        prices = self._parse_prices(xml_text)
        if not prices:
            raise EntsoeApiError("No price data available from ENTSO-E")
        _LOGGER.info("Received %s price points from ENTSO-E.", len(prices))
        return self._convert_prices(prices, now)

    async def _fetch_prices_xml(self, start: str, end: str) -> str:
        params = {
            "securityToken": self.security_token,
            "documentType": "A44",
            "contract_MarketAgreement.type": "A01",
            "in_Domain": self.domain,
            "out_Domain": self.domain,
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
                raise EntsoeApiError(f"Error communicating with ENTSO-E: {err}") from err
        else:
            text, status = await self._fetch_with_stdlib(params)

        if status != 200:
            raise EntsoeApiError(
                f"Failed to fetch ENTSO-E data: {status} - {text}"
            )

        _LOGGER.info(
            "Successfully fetched ENTSO-E data with response code %s.",
            status,
        )

        return text

    def _period_range(self, now: datetime | None) -> tuple[str, str]:
        current = self._to_entsoe_timezone(self._ensure_utc(now))
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
            raise EntsoeApiError(f"Invalid XML response: {err}") from err

        namespace_uri = self._detect_namespace(root.tag)
        namespace = {"ns": namespace_uri} if namespace_uri is not None else {}
        prefix = "ns:" if namespace else ""
        points: list[PricePoint] = []

        for series in root.findall(f".//{prefix}TimeSeries", namespace):
            for period in series.findall(f"{prefix}Period", namespace):
                start_text = period.findtext(
                    f"{prefix}timeInterval/{prefix}start", namespaces=namespace
                )
                resolution_text = period.findtext(
                    f"{prefix}resolution", namespaces=namespace
                )
                resolution_minutes = self._resolution_to_minutes(resolution_text)
                if start_text is None or resolution_minutes is None:
                    continue
                start_time = self._parse_datetime(start_text)
                if start_time is None:
                    continue
                for point in period.findall(f"{prefix}Point", namespace):
                    position_text = point.findtext(
                        f"{prefix}position", namespaces=namespace
                    )
                    price_text = point.findtext(
                        f"{prefix}price.amount", namespaces=namespace
                    )
                    if position_text is None or price_text is None:
                        continue
                    try:
                        position = int(position_text)
                        price = Decimal(price_text)
                    except (ValueError, InvalidOperation):
                        continue
                    timestamp = start_time + timedelta(
                        minutes=resolution_minutes * (position - 1)
                    )
                    points.append(
                        PricePoint(
                            timestamp=timestamp,
                            price_eur_mwh=price,
                            resolution_minutes=resolution_minutes,
                        )
                    )

        points.sort(key=lambda item: item.timestamp)
        return points

    @staticmethod
    def _detect_namespace(tag: str) -> str | None:
        if tag.startswith("{") and "}" in tag:
            closing_index = tag.find("}")
            return tag[1:closing_index]
        return None

    @staticmethod
    def _resolution_to_minutes(value: str | None) -> int | None:
        if value is None:
            return None
        normalized = value.strip()
        mapping = {
            "PT5M": 5,
            "PT10M": 10,
            "PT15M": 15,
            "PT20M": 20,
            "PT30M": 30,
            "PT60M": 60,
            "PT1H": 60,
        }
        if normalized in mapping:
            return mapping[normalized]
        return None

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

        converted_points: list[ConvertedPoint] = []

        for point in prices:
            converted_value = (point.price_eur_mwh / energy_divisor) * conversion_rate
            converted_value *= vat_multiplier
            converted_value = converted_value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            converted_points.append(
                ConvertedPoint(
                    start=point.timestamp,
                    value=converted_value,
                    raw_value=point.price_eur_mwh,
                    resolution_minutes=point.resolution_minutes,
                )
            )

        converted_points.sort(key=lambda item: item.start)
        points_by_resolution: dict[int, list[ConvertedPoint]] = {}
        for item in converted_points:
            points_by_resolution.setdefault(item.resolution_minutes, []).append(item)

        unit = f"{self.currency}/{self.energy_unit}"
        series: dict[str, Any] = {}

        quarter_points = points_by_resolution.get(15)
        if quarter_points:
            series["quarter_hour"] = self._build_series_from_points(
                quarter_points,
                15,
                current_time,
            )

        half_hour_points = points_by_resolution.get(30)
        if half_hour_points:
            series["half_hour"] = self._build_series_from_points(
                half_hour_points,
                30,
                current_time,
            )

        hour_points = points_by_resolution.get(60)
        if hour_points is None:
            hour_points = self._build_hour_entries(converted_points)
        if hour_points:
            series["hour"] = self._build_series_from_points(
                hour_points,
                60,
                current_time,
            )

        return {
            "unit": unit,
            ATTR_SERIES: series,
            ATTR_PRICE_FIELDS: [
                ATTR_PRICE_ID,
                ATTR_PRICE_START,
                ATTR_VALUE,
                ATTR_RAW_PRICE,
            ],
            ATTR_UPDATED_AT: datetime.now(timezone.utc).isoformat(),
        }

    def _build_series_from_points(
        self,
        items: list[ConvertedPoint],
        resolution_minutes: int,
        current_time: datetime,
    ) -> dict[str, Any]:
        today_items = [
            item for item in items if item.start.date() == current_time.date()
        ]
        tomorrow_items = [
            item
            for item in items
            if item.start.date() == (current_time + timedelta(days=1)).date()
        ]
        current_value = self._find_current_value(items, resolution_minutes, current_time)
        resolution_text = self._minutes_to_resolution(resolution_minutes)

        today_serialized = self._serialize_prices(
            today_items,
            resolution_text,
            resolution_minutes,
        )
        tomorrow_serialized = self._serialize_prices(
            tomorrow_items,
            resolution_text,
            resolution_minutes,
        )
        return {
            "current": float(current_value) if current_value is not None else None,
            ATTR_PRICES_TODAY: today_serialized,
            ATTR_PRICES_TOMORROW: tomorrow_serialized,
        }

    def _serialize_prices(
        self,
        items: list[ConvertedPoint],
        resolution: str,
        duration_minutes: int,
    ) -> dict[str, Any]:
        sorted_items = sorted(items, key=lambda item: item.start)
        return {
            ATTR_DURATION_MINUTES: duration_minutes,
            ATTR_PRICE_ID: [
                f"{resolution}-{int(item.start.timestamp())}" for item in sorted_items
            ],
            ATTR_PRICE_START: [item.start.isoformat() for item in sorted_items],
            ATTR_VALUE: [float(item.value) for item in sorted_items],
            ATTR_RAW_PRICE: [float(item.raw_value) for item in sorted_items],
        }

    def _build_hour_entries(self, items: list[ConvertedPoint]) -> list[ConvertedPoint]:
        grouped: dict[datetime, list[ConvertedPoint]] = {}
        for item in items:
            hour_start = item.start.replace(minute=0, second=0, microsecond=0)
            grouped.setdefault(hour_start, []).append(item)

        results: list[ConvertedPoint] = []
        for hour_start, hour_items in grouped.items():
            if not hour_items:
                continue
            count = Decimal(len(hour_items))
            value_sum = sum((point.value for point in hour_items), Decimal(0))
            raw_sum = sum((point.raw_value for point in hour_items), Decimal(0))
            results.append(
                ConvertedPoint(
                    start=hour_start,
                    value=(value_sum / count).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
                    raw_value=(raw_sum / count).quantize(
                        Decimal("0.0001"), rounding=ROUND_HALF_UP
                    ),
                    resolution_minutes=60,
                )
            )

        return sorted(results, key=lambda item: item.start)

    def _find_current_value(
        self,
        items: list[ConvertedPoint],
        resolution_minutes: int,
        current_time: datetime,
    ) -> Decimal | None:
        if not items:
            return None
        sorted_items = sorted(items, key=lambda item: item.start)
        for item in sorted_items:
            period_end = item.start + timedelta(minutes=resolution_minutes)
            if item.start <= current_time < period_end:
                return item.value
        for item in sorted_items:
            if item.start >= current_time:
                return item.value
        return sorted_items[-1].value

    @staticmethod
    def _minutes_to_resolution(minutes: int) -> str:
        mapping = {
            5: "PT5M",
            10: "PT10M",
            15: "PT15M",
            20: "PT20M",
            30: "PT30M",
            60: "PT60M",
        }
        return mapping.get(minutes, f"PT{minutes}M")

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

    def _to_entsoe_timezone(self, value: datetime) -> datetime:
        timezone_info = self.ENTSOE_TIMEZONE
        if timezone_info is not None:
            return value.astimezone(timezone_info)
        manual_timezone = timezone(
            self._brussels_offset_for(value),
            name=self._brussels_tz_name(value),
        )
        return value.astimezone(manual_timezone)

    @staticmethod
    def _brussels_offset_for(value: datetime) -> timedelta:
        reference = value.astimezone(timezone.utc)
        year = reference.year
        dst_start = EntsoeApiClient._last_sunday_utc(year, 3)
        dst_end = EntsoeApiClient._last_sunday_utc(year, 10)
        if dst_start <= reference < dst_end:
            return timedelta(hours=2)
        return timedelta(hours=1)

    @staticmethod
    def _brussels_tz_name(value: datetime) -> str:
        return "CEST" if EntsoeApiClient._brussels_offset_for(value) == timedelta(hours=2) else "CET"

    @staticmethod
    def _last_sunday_utc(year: int, month: int) -> datetime:
        last_day = calendar.monthrange(year, month)[1]
        candidate = datetime(year, month, last_day, 1, tzinfo=timezone.utc)
        while candidate.weekday() != 6:
            candidate -= timedelta(days=1)
        return candidate
