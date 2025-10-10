from __future__ import annotations

import asyncio
import calendar
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

from .constants import ENTSOE_API_URL, REQUEST_TIMEOUT
from .models import SeriesData


class EntsoeApiError(Exception):
    """Exception raised when communication with ENTSO-E fails."""


@dataclass
class PricePoint:
    timestamp: datetime
    price_eur_mwh: Decimal


@dataclass
class ConvertedPoint:
    start: datetime
    value: Decimal


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

    async def get_converted_prices(self, now: datetime | None = None) -> dict[str, SeriesData]:
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
                    points.append(PricePoint(timestamp=timestamp, price_eur_mwh=price))

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
    ) -> dict[str, SeriesData]:
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
                )
            )

        converted_points.sort(key=lambda item: item.start)

        if not converted_points:
            raise EntsoeApiError("No price data available from ENTSO-E")

        base_step = self._infer_step_minutes(converted_points)
        updated_at = datetime.now(timezone.utc)

        quarter_series = self._create_series_data(
            points=converted_points,
            current_time=current_time,
            step_minutes=base_step,
            updated_at=updated_at,
        )

        hour_entries = self._build_hour_entries(converted_points, base_step)
        hour_series = self._create_series_data(
            points=hour_entries,
            current_time=current_time,
            step_minutes=60,
            updated_at=updated_at,
        )

        return {
            "quarter_hour": quarter_series,
            "hour": hour_series,
        }

    def _build_hour_entries(
        self,
        items: list[ConvertedPoint],
        base_step: int,
    ) -> list[ConvertedPoint]:
        if not items:
            return []

        if base_step >= 60:
            return [
                ConvertedPoint(
                    start=item.start.replace(minute=0, second=0, microsecond=0),
                    value=item.value,
                )
                for item in items
            ]

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
                )
            )

        return sorted(results, key=lambda item: item.start)

    def _create_series_data(
        self,
        points: list[ConvertedPoint],
        current_time: datetime,
        step_minutes: int,
        updated_at: datetime,
    ) -> SeriesData:
        today_date = current_time.date()
        tomorrow_date = (current_time + timedelta(days=1)).date()

        max_points = self._max_points_for_step(step_minutes)

        today_points = [
            item for item in points if item.start.date() == today_date
        ][:max_points]
        tomorrow_points = [
            item for item in points if item.start.date() == tomorrow_date
        ][:max_points]

        today_values = tuple(self._float_value(item.value) for item in today_points)
        tomorrow_values_list = [self._float_value(item.value) for item in tomorrow_points]
        tomorrow_values = (
            tuple(tomorrow_values_list) if tomorrow_values_list else None
        )

        reference_point = (
            today_points[0].start
            if today_points
            else (tomorrow_points[0].start if tomorrow_points else current_time)
        )
        start_local = self._to_entsoe_timezone(reference_point).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        current_decimal = self._find_current_value(points, current_time, step_minutes)
        current_value = self._float_value(current_decimal) if current_decimal is not None else None

        today_min, today_max, today_avg = self._calculate_stats(today_values)
        tomorrow_min = tomorrow_max = tomorrow_avg = None
        if tomorrow_values is not None:
            tomorrow_min, tomorrow_max, tomorrow_avg = self._calculate_stats(tomorrow_values)

        return SeriesData(
            current=current_value,
            start=start_local,
            step_minutes=step_minutes,
            today=today_values,
            tomorrow=tomorrow_values,
            today_min=today_min,
            today_max=today_max,
            today_avg=today_avg,
            tomorrow_min=tomorrow_min,
            tomorrow_max=tomorrow_max,
            tomorrow_avg=tomorrow_avg,
            updated_at=updated_at,
            currency=self.currency,
            unit=f"{self.currency}/{self.energy_unit}",
            in_domain=self.domain,
            out_domain=self.domain,
            source="ENTSO-E",
        )

    @staticmethod
    def _float_value(value: Decimal) -> float:
        return round(float(value), 4)

    @staticmethod
    def _calculate_stats(values: tuple[float, ...]) -> tuple[float | None, float | None, float | None]:
        if not values:
            return None, None, None
        minimum = round(min(values), 4)
        maximum = round(max(values), 4)
        average = round(sum(values) / len(values), 4)
        return minimum, maximum, average

    @staticmethod
    def _max_points_for_step(step_minutes: int) -> int:
        if step_minutes <= 0:
            return 96
        return min(96, max(1, 1440 // step_minutes))

    @staticmethod
    def _infer_step_minutes(points: list[ConvertedPoint]) -> int:
        if len(points) < 2:
            return 15
        deltas: list[int] = []
        for index in range(len(points) - 1):
            delta = int(
                (points[index + 1].start - points[index].start).total_seconds() // 60
            )
            if delta > 0:
                deltas.append(delta)
        if not deltas:
            return 15
        return min(deltas)

    def _find_current_value(
        self,
        points: list[ConvertedPoint],
        current_time: datetime,
        step_minutes: int,
    ) -> Decimal | None:
        if not points:
            return None

        slot_minute = (current_time.minute // step_minutes) * step_minutes
        slot_start = current_time.replace(minute=slot_minute)

        price_map = {item.start: item.value for item in points}
        if slot_start in price_map:
            return price_map[slot_start]

        for item in points:
            if item.start > slot_start:
                return item.value

        return points[-1].value

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
