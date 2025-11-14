from __future__ import annotations
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DOMAIN, CONF_STOP_NUMBER, CONF_LINES, CONF_NAME, CONF_SCAN_INTERVAL, CONF_ONLY_TRAMS,
    DEFAULT_NAME, DEFAULT_SCAN_INTERVAL, DEFAULT_ONLY_TRAMS, API_URL,
)
from .api import RozkladyAPI

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STOP_NUMBER): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_LINES): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                user_input[CONF_STOP_NUMBER] = int(user_input[CONF_STOP_NUMBER])
            except Exception:
                errors["base"] = "cannot_connect"
                return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)

            await self.async_set_unique_id(f"stop_{user_input[CONF_STOP_NUMBER]}")
            self._abort_if_unique_id_configured()

            try:
                session = async_get_clientsession(self.hass)
                api = RozkladyAPI(session, API_URL)
                xml = await api.fetch_xml(int(user_input[CONF_STOP_NUMBER]))
                _ = api.parse(xml, only_trams=True)
                return self.async_create_entry(title=f"Przystanek {user_input[CONF_STOP_NUMBER]}", data=user_input)
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.config_entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        number_cfg = selector.NumberSelectorConfig(
            min=30, max=600, step=30, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="s"
        )

        options_schema = vol.Schema(
            {
                vol.Optional(CONF_LINES, default=self.config_entry.data.get(CONF_LINES, "")): str,
                vol.Optional(CONF_SCAN_INTERVAL, default=self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): selector.NumberSelector(number_cfg),
                vol.Optional(CONF_ONLY_TRAMS, default=self.config_entry.options.get(CONF_ONLY_TRAMS, DEFAULT_ONLY_TRAMS)): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=options_schema)
