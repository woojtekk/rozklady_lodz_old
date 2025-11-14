from __future__ import annotations
from typing import Any
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, CONF_STOP_NUMBER, CONF_LINES, CONF_NAME, CONF_SCAN_INTERVAL, CONF_ONLY_TRAMS, DEFAULT_ONLY_TRAMS, DEFAULT_SCAN_INTERVAL
from .coordinator import RozkladyCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    stop_number = int(entry.data[CONF_STOP_NUMBER])
    lines = [l.strip() for l in str(entry.data[CONF_LINES]).split(",") if l.strip()]
    name_prefix = entry.data.get(CONF_NAME) or "Rozkłady Łódź"

    scan = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    only_trams = entry.options.get(CONF_ONLY_TRAMS, DEFAULT_ONLY_TRAMS)

    coordinator = RozkladyCoordinator(hass, stop_number, scan, only_trams)
    await coordinator.async_config_entry_first_refresh()

    entities: list[SensorEntity] = [DepartureSensor(coordinator, entry, line, name_prefix) for line in lines]
    async_add_entities(entities)

class DepartureSensor(CoordinatorEntity[RozkladyCoordinator], SensorEntity):
    _attr_icon = "mdi:tram"
    _attr_native_unit_of_measurement = "min"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: RozkladyCoordinator, entry: ConfigEntry, line: str, name_prefix: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._line = line
        self._attr_unique_id = f"{entry.entry_id}_line_{line}"
        self._attr_name = f"{name_prefix} {line}"

    @property
    def device_info(self) -> DeviceInfo:
        stop = self._entry.data.get(CONF_STOP_NUMBER)
        return DeviceInfo(
            identifiers={(DOMAIN, f"stop_{stop}")},
            name=f"Rozkłady Łódź ({stop})",
            manufacturer="rozklady.lodz.pl",
            model="Realtime departures",
        )

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data or {}
        deps = (data.get("departures") or {}).get(self._line)
        if not deps:
            return None
        for item in deps["items"]:
            if item["minutes"] is not None:
                return int(item["minutes"])
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        stop_name = data.get("stop_name")
        deps = (data.get("departures") or {}).get(self._line) or {}
        direction = deps.get("dir")
        items = deps.get("items") or []

        minutes_list = [int(i["minutes"]) for i in items if i["minutes"] is not None]
        pretty_list = [i["pretty"] for i in items]

        return {
            "stop_name": stop_name,
            "direction": direction,
            "minutes_list": minutes_list,
            "pretty_list": pretty_list,
            "line": self._line,
        }
