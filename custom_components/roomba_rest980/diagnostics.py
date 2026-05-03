"""Diagnostics support for roomba_rest980."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

TO_REDACT = {
    "irobot_username",
    "irobot_password",
    "robot_blid",
    "blid",
    "password",
    "deploymentId",
    "macAddress",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return redacted config entry + last coordinator data."""
    runtime = entry.runtime_data
    local_data = (
        runtime.local_coordinator.data if runtime.local_coordinator else None
    ) or {}
    cloud_data = (
        runtime.cloud_coordinator.data if runtime.cloud_coordinator else None
    ) or {}

    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "unique_id": entry.unique_id,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "runtime": {
            "cloud_enabled": runtime.cloud_enabled,
            "robot_blid_present": bool(runtime.robot_blid),
        },
        "local_data": async_redact_data(local_data, TO_REDACT),
        "cloud_data": async_redact_data(cloud_data, TO_REDACT),
    }
