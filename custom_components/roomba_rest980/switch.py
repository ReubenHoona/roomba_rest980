"""Switch entities exposing rest980 config toggles."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up rest980 config switches."""
    coordinator = entry.runtime_data.local_coordinator
    async_add_entities(
        [
            RoombaEdgeCleanSwitch(coordinator, entry),
            RoombaAlwaysFinishSwitch(coordinator, entry),
        ]
    )


class _RoombaConfigSwitch(CoordinatorEntity, SwitchEntity):
    """Base class for rest980 boolean config toggles."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    _name: str
    _slug: str
    _on_path: str
    _off_path: str

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = self._name
        self._attr_unique_id = f"{entry.unique_id}_{self._slug}"

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.unique_id)},
            name=data.get("name", "Roomba"),
            manufacturer="iRobot",
            model="Roomba",
            model_id=data.get("sku"),
            sw_version=data.get("softwareVer"),
        )

    async def _post(self, path: str) -> None:
        session = async_get_clientsession(self.hass)
        url = f"{self._entry.data['base_url']}/api/local/config/{path}"
        try:
            async with session.post(url) as resp:
                resp.raise_for_status()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Failed to POST %s: %s", url, err)
            return
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs) -> None:
        await self._post(self._on_path)

    async def async_turn_off(self, **kwargs) -> None:
        await self._post(self._off_path)


class RoombaEdgeCleanSwitch(_RoombaConfigSwitch):
    """Edge cleaning toggle."""

    _name = "Edge Cleaning"
    _slug = "edge_clean_switch"
    _on_path = "edgeClean/on"
    _off_path = "edgeClean/off"
    _attr_icon = "mdi:wall"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data or {}
        open_only = data.get("openOnly")
        if open_only is None:
            return None
        return not open_only


class RoombaAlwaysFinishSwitch(_RoombaConfigSwitch):
    """Always-finish (ignore full bin) toggle."""

    _name = "Always Finish"
    _slug = "always_finish_switch"
    _on_path = "alwaysFinish/on"
    _off_path = "alwaysFinish/off"
    _attr_icon = "mdi:flag-checkered"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data or {}
        bin_pause = data.get("binPause")
        if bin_pause is None:
            return None
        return not bin_pause
