from __future__ import annotations

from datetime import timedelta
import logging

from aiohttp import ClientSession
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .shared.api import EntsoeApiClient, EntsoeApiError
from .shared.models import SeriesData

_LOGGER = logging.getLogger(__name__)


class EntsoeCoordinator(DataUpdateCoordinator[dict[str, SeriesData]]):
    def __init__(
        self,
        hass: HomeAssistant,
        session: ClientSession,
        security_token: str,
        domain: str,
        currency: str,
        energy_unit: str,
        vat: float,
        currency_rate: float,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="ENTSO-E Energy Prices",
            update_interval=update_interval,
        )
        self.api_client = EntsoeApiClient(
            session=session,
            security_token=security_token,
            domain=domain,
            currency=currency,
            energy_unit=energy_unit,
            vat=vat,
            currency_rate=currency_rate,
        )

    async def _async_update_data(self) -> dict[str, SeriesData]:
        try:
            return await self.api_client.get_converted_prices()
        except EntsoeApiError as err:
            raise UpdateFailed(str(err)) from err
