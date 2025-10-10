from __future__ import annotations

import asyncio
import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
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
    ATTR_CURRENT,
    ATTR_CURRENCY,
    ATTR_IN_DOMAIN,
    ATTR_OUT_DOMAIN,
    ATTR_SERIES,
    ATTR_SOURCE,
    ATTR_START,
    ATTR_STEP_MINUTES,
    ATTR_TODAY,
    ATTR_TODAY_AVG,
    ATTR_TODAY_MAX,
    ATTR_TODAY_MIN,
    ATTR_TOMORROW,
    ATTR_TOMORROW_AVG,
    ATTR_TOMORROW_MAX,
    ATTR_TOMORROW_MIN,
    ATTR_UNIT,
    ATTR_UPDATED_AT,
    ENTSOE_API_URL,
    REQUEST_TIMEOUT,
)


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
        xml_text = await self._fetch_prices_xml(start, end)
        prices = self._parse_prices(xml_text)
        if not prices:
            raise EntsoeApiError("No price data available from ENTSO-E")
        return self._convert_prices(prices, now)

    async def _fetch_prices_xml(self, start: str, end: str) -> str:
        params = {
            "securityToken": self.security_token,
            "documentType": "A44",
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
            "PT15M": 15,
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
        current_local = self._to_entsoe_timezone(current_time)
        conversion_rate = Decimal(str(self.currency_rate))
        vat_multiplier = Decimal("1") + (Decimal(str(self.vat)) / Decimal("100"))
        energy_divisor = Decimal("1000") if self.energy_unit == "kWh" else Decimal("1")

        converted_points: list[ConvertedPoint] = []

        for point in prices:
            converted_value = (point.price_eur_mwh / energy_divisor) * conversion_rate
            converted_value *= vat_multiplier
            converted_value = converted_value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            converted_points.append(
                ConvertedPoint(
                    start=point.timestamp,
                    value=converted_value,
                    resolution_minutes=point.resolution_minutes,
                )
            )

        if not converted_points:
            raise EntsoeApiError("No converted price points available")

        base_resolution = min(item.resolution_minutes for item in converted_points)
        quarter_points = [item for item in converted_points if item.resolution_minutes == base_resolution]
        if not quarter_points:
            quarter_points = converted_points

        hour_points = self._build_hour_entries(converted_points)

        quarter_series = self._build_series_payload(
            quarter_points,
            base_resolution,
            current_time,
            current_local,
        )

        hour_series = self._build_series_payload(
            hour_points,
            60,
            current_time,
            current_local,
        )

        unit = f"{self.currency}/{self.energy_unit}"
        timestamp_now = datetime.now(timezone.utc).isoformat()

        return {
            ATTR_UNIT: unit,
            ATTR_CURRENCY: self.currency,
            ATTR_UPDATED_AT: timestamp_now,
            ATTR_SOURCE: "ENTSO-E",
            ATTR_IN_DOMAIN: self.domain,
            ATTR_OUT_DOMAIN: self.domain,
            ATTR_SERIES: {
                "quarter_hour": quarter_series,
                "hour": hour_series,
            },
        }

    def _build_series_payload(
        self,
        items: list[ConvertedPoint],
        step_minutes: int,
        current_time: datetime,
        current_local: datetime,
    ) -> dict[str, Any]:
        sorted_items = sorted(items, key=lambda item: item.start)
        today_date = current_local.date()
        tomorrow_date = (current_local + timedelta(days=1)).date()
        slots_per_day = self._slots_per_day(step_minutes)

        today_values = self._values_for_date(sorted_items, today_date, slots_per_day)
        tomorrow_values = self._values_for_date(sorted_items, tomorrow_date, slots_per_day)

        start_reference = self._series_start(sorted_items, current_local)

        payload: dict[str, Any] = {
            ATTR_CURRENT: self._select_current_value(sorted_items, current_time, step_minutes),
            ATTR_START: start_reference,
            ATTR_STEP_MINUTES: step_minutes,
            ATTR_TODAY: today_values,
        }

        payload.update(self._stats_for_today(today_values))

        if tomorrow_values:
            payload[ATTR_TOMORROW] = tomorrow_values
            payload.update(self._stats_for_tomorrow(tomorrow_values))

        return payload

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
            results.append(
                ConvertedPoint(
                    start=hour_start,
                    value=(value_sum / count).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
                    resolution_minutes=60,
                )
            )

        return sorted(results, key=lambda item: item.start)

    @staticmethod
    def _slots_per_day(step_minutes: int) -> int:
        if step_minutes <= 0:
            return 1
        return max(1, (24 * 60) // step_minutes)

    def _values_for_date(
        self,
        items: list[ConvertedPoint],
        target_date: date,
        limit: int,
    ) -> list[float]:
        filtered: list[float] = []
        for item in items:
            localized = self._to_entsoe_timezone(item.start)
            if localized.date() == target_date:
                filtered.append(self._round_float(item.value))
        return filtered[:limit]

    def _series_start(
        self,
        items: list[ConvertedPoint],
        current_local: datetime,
    ) -> str:
        if items:
            reference = self._to_entsoe_timezone(items[0].start)
        else:
            reference = current_local
        start_of_day = reference.replace(hour=0, minute=0, second=0, microsecond=0)
        return start_of_day.isoformat()

    def _select_current_value(
        self,
        items: list[ConvertedPoint],
        current_time: datetime,
        step_minutes: int,
    ) -> float | None:
        if not items:
            return None
        step = max(step_minutes, 1)
        minute = (current_time.minute // step) * step
        slot = current_time.replace(minute=minute, second=0, microsecond=0)
        value_map = {item.start: item.value for item in items}
        selected = value_map.get(slot)
        if selected is None:
            past_items = [item for item in items if item.start <= slot]
            if past_items:
                selected = past_items[-1].value
            else:
                future_items = [item for item in items if item.start >= slot]
                if not future_items:
                    return None
                selected = future_items[0].value
        return self._round_float(selected)

    def _stats_for_today(self, values: list[float]) -> dict[str, float]:
        if not values:
            return {}
        return {
            ATTR_TODAY_MIN: self._round_float(min(values)),
            ATTR_TODAY_MAX: self._round_float(max(values)),
            ATTR_TODAY_AVG: self._round_float(sum(values) / len(values)),
        }

    def _stats_for_tomorrow(self, values: list[float]) -> dict[str, float]:
        if not values:
            return {}
        return {
            ATTR_TOMORROW_MIN: self._round_float(min(values)),
            ATTR_TOMORROW_MAX: self._round_float(max(values)),
            ATTR_TOMORROW_AVG: self._round_float(sum(values) / len(values)),
        }

    @staticmethod
    def _round_float(value: Decimal | float) -> float:
        decimal_value = Decimal(str(value))
        return float(decimal_value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))

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
