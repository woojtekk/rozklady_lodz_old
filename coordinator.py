from __future__ import annotations
import logging
from datetime import timedelta
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import API_URL, DEFAULT_SCAN_INTERVAL
from .api import RozkladyAPI

_LOGGER = logging.getLogger(__name__)

class RozkladyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, stop_number: int, scan_interval: int, only_trams: bool) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="rozklady_lodz",
            update_interval=timedelta(seconds=scan_interval or DEFAULT_SCAN_INTERVAL),
        )
        self._stop = stop_number
        self._only_trams = only_trams
        self._api = RozkladyAPI(async_get_clientsession(hass), API_URL)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            xml = await self._api.fetch_xml(self._stop)
            data = self._api.parse(xml, only_trams=self._only_trams)
            return data
        except Exception as err:
            raise UpdateFailed(f"Update failed: {err}") from err
