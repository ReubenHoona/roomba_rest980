"""Select entities for Roomba rest980 — config toggles and per-room cleaning."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, regionTypeMappings, zoneTypeMappings

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up local config selects and (when ready) cloud per-room selects."""
    coordinator = entry.runtime_data.local_coordinator
    async_add_entities(
        [
            RoombaCarpetBoostSelect(coordinator, entry),
            RoombaCleaningPassesSelect(coordinator, entry),
        ]
    )

    cloud_coordinator = entry.runtime_data.cloud_coordinator
    if not cloud_coordinator:
        return

    added = False

    @callback
    def _maybe_add_cloud_room_selects() -> None:
        nonlocal added
        if added:
            return
        if not cloud_coordinator.data:
            return
        blid = entry.runtime_data.robot_blid
        if not blid or blid not in cloud_coordinator.data:
            return
        cloud_data = cloud_coordinator.data[blid]
        if "pmaps" not in cloud_data:
            return

        entities: list[CleanRoomPasses] = []
        for pmap in cloud_data["pmaps"]:
            try:
                entities.extend(
                    CleanRoomPasses(
                        entry, region["name"] or "Unnamed Room", region, pmap
                    )
                    for region in pmap["active_pmapv_details"]["regions"]
                )
                entities.extend(
                    CleanRoomPasses(
                        entry, region["name"] or "Unnamed Zone", region, pmap, True
                    )
                    for region in pmap["active_pmapv_details"]["zones"]
                )
            except (KeyError, TypeError) as e:
                _LOGGER.warning(
                    "Failed to create pmap entity for %s: %s",
                    pmap.get("pmap_id", "unknown"),
                    e,
                )

        for ent in entities:
            entry.runtime_data.switched_rooms[f"select.{ent.unique_id}"] = ent
        async_add_entities(entities)
        added = True

    _maybe_add_cloud_room_selects()
    if not added:
        unsub = cloud_coordinator.async_add_listener(_maybe_add_cloud_room_selects)
        entry.async_on_unload(unsub)


class _RoombaConfigSelect(CoordinatorEntity, SelectEntity):
    """Base class for rest980 config-mapped select entities."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    _name: str
    _slug: str
    _path_prefix: str

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

    async def _post(self, suffix: str) -> None:
        session = async_get_clientsession(self.hass)
        url = f"{self._entry.data['base_url']}/api/local/config/{self._path_prefix}/{suffix}"
        try:
            async with session.post(url) as resp:
                resp.raise_for_status()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Failed to POST %s: %s", url, err)
            return
        await self.coordinator.async_request_refresh()


class RoombaCarpetBoostSelect(_RoombaConfigSelect):
    """Carpet boost mode (Auto/Performance/Eco)."""

    _name = "Carpet Boost Mode"
    _slug = "carpet_boost_select"
    _path_prefix = "carpetBoost"
    _attr_icon = "mdi:rug"
    _attr_options = ["Auto", "Performance", "Eco"]

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data or {}
        carpet_boost = data.get("carpetBoost")
        vac_high = data.get("vacHigh")
        if carpet_boost is None or vac_high is None:
            return None
        if carpet_boost:
            return "Auto"
        if vac_high:
            return "Performance"
        return "Eco"

    async def async_select_option(self, option: str) -> None:
        await self._post(option.lower())


class RoombaCleaningPassesSelect(_RoombaConfigSelect):
    """Cleaning passes setting (Auto/One/Two)."""

    _name = "Cleaning Passes"
    _slug = "cleaning_passes_select"
    _path_prefix = "cleaningPasses"
    _attr_icon = "mdi:broom"
    _attr_options = ["Auto", "One", "Two"]

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data or {}
        no_auto = data.get("noAutoPasses")
        two_pass = data.get("twoPass")
        if no_auto is None or two_pass is None:
            return None
        if not no_auto:
            return "Auto"
        return "Two" if two_pass else "One"

    async def async_select_option(self, option: str) -> None:
        await self._post(option.lower())


class CleanRoomPasses(SelectEntity):
    """A number entity to determine how many passes a room should be cleaned with."""

    def __init__(self, entry, name, data, pmap, zone=False) -> None:
        """Creates a switch entity for rooms."""
        self._attr_name = (
            f"Clean {pmap['active_pmapv_details']['map_header']['name']}: {name}"
        )
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_p_{data['id']}_{'z' if zone else 'r'}_{pmap['active_pmapv_details']['active_pmapv']['pmap_id']}"
        self._attached = f"{entry.unique_id}_{data['id']}_{'z' if zone else 'r'}_{pmap['active_pmapv_details']['active_pmapv']['pmap_id']}"
        self.pmap_id = pmap["active_pmapv_details"]["active_pmapv"]["pmap_id"]
        self._attr_current_option = "Don't Clean"
        self._attr_options = ["Don't Clean", "One Pass", "Two Passes"]
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "iRobot",
        }
        self.room_json = {
            "region_id": data["id"],
            "type": "rid",
            "params": {"noAutoPasses": False, "twoPass": False},
        }
        self._attr_extra_state_attributes = {
            "room_data": data,
            "room_json": self.room_json,
        }
        if zone:
            self.room_json["type"] = "zid"
            icon = zoneTypeMappings.get(
                data["zone_type"], zoneTypeMappings.get("default")
            )
        else:
            # autodetect icon
            icon = regionTypeMappings.get(
                data["region_type"], regionTypeMappings.get("default")
            )
        self._attr_icon = icon

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option == "Two Passes":
            self.room_json["params"] = {"noAutoPasses": True, "twoPass": True}
        elif option == "One Pass":
            self.room_json["params"] = {"noAutoPasses": False, "twoPass": False}
        self._attr_extra_state_attributes["room_json"] = self.room_json
        self._attr_current_option = option
        self._async_write_ha_state()

    def get_region_json(self):
        """Return robot-readable JSON to identify the room to start cleaning it."""
        return self.room_json
