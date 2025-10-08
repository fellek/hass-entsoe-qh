from __future__ import annotations

DOMAIN = "entsoe_qh"
PLATFORMS: list[str] = ["sensor"]
ENTSOE_API_URL = "https://web-api.tp.entsoe.eu/api"
REQUEST_TIMEOUT = 30

CONF_SECURITY_TOKEN = "security_token"
CONF_IN_DOMAIN = "in_domain"
CONF_OUT_DOMAIN = "out_domain"
CONF_CURRENCY = "currency"
CONF_ENERGY_UNIT = "energy_unit"
CONF_CURRENCY_RATE = "currency_rate"
CONF_VAT = "vat"

DEFAULT_IN_DOMAIN = "10YPL-AREA-----S"
DEFAULT_OUT_DOMAIN = "10YPL-AREA-----S"
DEFAULT_CURRENCY = "EUR"
DEFAULT_ENERGY_UNIT = "kWh"

SUPPORTED_CURRENCIES = {"EUR", "PLN"}
SUPPORTED_ENERGY_UNITS = {"kWh", "MWh"}

ATTR_PRICES_TODAY = "prices_today"
ATTR_PRICES_TOMORROW = "prices_tomorrow"
ATTR_RAW_PRICE = "price_eur_mwh"
ATTR_UPDATED_AT = "updated_at"
