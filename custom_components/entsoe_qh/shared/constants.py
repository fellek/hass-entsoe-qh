from __future__ import annotations

from typing import Final

DOMAIN = "entsoe_qh"
PLATFORMS: list[str] = ["sensor"]
ENTSOE_API_URL = "https://web-api.tp.entsoe.eu/api"
REQUEST_TIMEOUT = 30

CONF_SECURITY_TOKEN = "security_token"
CONF_DOMAIN = "domain"
CONF_CURRENCY = "currency"
CONF_ENERGY_UNIT = "energy_unit"
CONF_CURRENCY_RATE = "currency_rate"
CONF_VAT = "vat"

DEFAULT_DOMAIN = "10YPL-AREA-----S"
DEFAULT_CURRENCY = "EUR"
DEFAULT_ENERGY_UNIT = "kWh"

SUPPORTED_CURRENCIES = {"EUR", "PLN"}
SUPPORTED_ENERGY_UNITS = {"kWh", "MWh"}

ENTSOE_DOMAIN_CHOICES: list[tuple[str, str]] = [
    ("Albania", "10YAL-KESH-----5"),
    ("Austria", "10YAT-APG------L"),
    ("Belgium", "10YBE----------2"),
    ("Bosnia and Herzegovina", "10YBA-JPCC-----D"),
    ("Bulgaria", "10YCA-BULGARIA-R"),
    ("Croatia", "10YHR-HEP------M"),
    ("Cyprus", "10YCY-1001A0003J"),
    ("Czech Republic", "10YCZ-CEPS-----N"),
    ("Denmark", "10YDK-1--------W"),
    ("Denmark", "10YDK-2--------M"),
    ("Estonia", "10Y1001A1001A39I"),
    ("Finland", "10YFI-1--------U"),
    ("France", "10YFR-RTE------C"),
    ("Georgia", "10Y1001A1001B012"),
    ("Greece", "10YGR-HTSO-----Y"),
    ("Germany-Luxembourg (DE-LU)","10Y1001A1001A82H"),
    ("Germany", "10YDE-VE-------2"),
    ("Germany", "10YDE-RWENET---I"),
    ("Germany", "10YDE-EON------1"),
    ("Germany", "10YDE-ENBW-----N"),
    ("Hungary", "10YHU-MAVIR----U"),
    ("Ireland", "10Y1001A1001A59C"),
    ("Ireland", "10YIE-1001A00010"),
    ("Italy", "10Y1001A1001A73I"),
    ("Italy", "10Y1001A1001A70O"),
    ("Italy", "10Y1001A1001A71M"),
    ("Italy", "10Y1001A1001A788"),
    ("Italy", "10Y1001A1001A75E"),
    ("Italy", "10Y1001A1001A74G"),
    ("Italy", "10Y1001A1001A72K"),
    ("Italy", "10Y1001A1001A77A"),
    ("Italy", "10Y1001A1001A76C"),
    ("Italy", "10Y1001A1001A699"),
    ("Kosovo", "10Y1001C--00100H"),
    ("Latvia", "10YLV-1001A00074"),
    ("Lithuania", "10YLT-1001A0008Q"),
    ("Luxembourg", "10YLU-CEGEDEL-NQ"),
    ("Malta", "10Y1001A1001A93C"),
    ("Moldova", "10Y1001A1001A990"),
    ("Montenegro", "10YCS-CG-TSO---S"),
    ("Netherlands", "10YNL----------L"),
    ("North Macedonia", "10YMK-MEPSO----8"),
    ("Norway", "10YNO-1--------2"),
    ("Norway", "10YNO-2--------T"),
    ("Norway", "10YNO-3--------J"),
    ("Norway", "10YNO-4--------9"),
    ("Norway", "10Y1001A1001A48H"),
    ("Poland", "10YPL-AREA-----S"),
    ("Portugal", "10YPT-REN------W"),
    ("Romania", "10YRO-TEL------P"),
    ("Serbia", "10YCS-SERBIATSOV"),
    ("Slovakia", "10YSK-SEPS-----K"),
    ("Slovenia", "10YSI-ELES-----O"),
    ("Spain", "10YES-REE------0"),
    ("Sweden", "10YSE-1--------K"),
    ("Sweden", "10Y1001A1001A45N"),
    ("Sweden", "10Y1001A1001A46L"),
    ("Sweden", "10Y1001A1001A47J"),
    ("Switzerland", "10YCH-SWISSGRIDZ"),
    ("Turkey", "10YTR-TEIAS----W"),
    ("Ukraine", "10Y1001C--00003F"),
    ("Ukraine", "10YUA-WEPS-----0"),
    ("United Kingdom", "10YGB----------A"),
]

ENTSOE_DOMAIN_EXPECTED_RESOLUTIONS: Final[dict[str, tuple[int, ...]]] = {
    domain: (60,) for _, domain in ENTSOE_DOMAIN_CHOICES
}

for half_hour_domain in ("10Y1001A1001A59C", "10YIE-1001A00010"):
    ENTSOE_DOMAIN_EXPECTED_RESOLUTIONS[half_hour_domain] = (30, 60)

ATTR_SERIES = "series"
ATTR_PRICES_TODAY = "prices_today"
ATTR_PRICES_TOMORROW = "prices_tomorrow"
ATTR_PRICE_ID = "id"
ATTR_PRICE_START = "start"
ATTR_DURATION_MINUTES = "duration_minutes"
ATTR_VALUE = "value"
ATTR_RAW_PRICE = "price_eur_mwh"
ATTR_UPDATED_AT = "updated_at"
ATTR_PRICE_FIELDS = "prices_fields"
ATTR_SERIES_TOTAL_POINTS = "total_points"
ATTR_SERIES_TRUNCATED = "truncated"
