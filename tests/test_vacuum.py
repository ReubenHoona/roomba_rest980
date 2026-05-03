"""Tests for vacuum.py — action methods and activity state machine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.roomba_rest980.vacuum import RoombaVacuum

from .conftest import make_post_mock


def _make_vacuum(coordinator, entry):
    """Build a RoombaVacuum with a fake hass."""
    hass = MagicMock()
    return RoombaVacuum(hass, coordinator, entry)


# -- Activity state machine ----------------------------------------------------


from homeassistant.components.vacuum import VacuumActivity


@pytest.mark.parametrize(
    "status,expected",
    [
        ({"cycle": "clean", "phase": "run", "notReady": 0}, VacuumActivity.CLEANING),
        ({"cycle": "quick", "phase": "run", "notReady": 0}, VacuumActivity.CLEANING),
        ({"cycle": "clean", "phase": "stop", "notReady": 0}, VacuumActivity.PAUSED),
        ({"cycle": "clean", "phase": "pause", "notReady": 0}, VacuumActivity.PAUSED),
        ({"cycle": "dock", "phase": "hmUsrDock", "notReady": 0}, VacuumActivity.RETURNING),
        ({"cycle": "evac", "phase": "evac", "notReady": 0}, VacuumActivity.DOCKED),
        ({"cycle": "none", "phase": "charge", "notReady": 0}, VacuumActivity.DOCKED),
        # NOTE: the state machine in vacuum.py is order-dependent — later if-blocks
        # override earlier ones. IDLE is only visible when notReady==0 AND no other
        # cycle/phase rule matches; ERROR is overridden whenever phase is in
        # {stop, pause}. See the order in _handle_coordinator_update().
        ({"cycle": "none", "phase": None, "notReady": 0}, VacuumActivity.IDLE),
        ({"cycle": "none", "phase": None, "notReady": 7}, VacuumActivity.ERROR),
    ],
)
def test_activity_state_machine(mock_coordinator, mock_entry, status, expected):
    mock_coordinator.data = {"cleanMissionStatus": status}
    vac = _make_vacuum(mock_coordinator, mock_entry)
    # Replace _async_write_ha_state to avoid HA wiring
    vac._async_write_ha_state = MagicMock()
    vac._handle_coordinator_update()
    assert vac._attr_activity == expected


def test_activity_paused_overrides_error_when_phase_stop(
    mock_coordinator, mock_entry
):
    """Document the existing behavior: phase=stop wins even when notReady>0."""
    mock_coordinator.data = {
        "cleanMissionStatus": {"cycle": "none", "phase": "stop", "notReady": 7}
    }
    vac = _make_vacuum(mock_coordinator, mock_entry)
    vac._async_write_ha_state = MagicMock()
    vac._handle_coordinator_update()
    assert vac._attr_activity == VacuumActivity.PAUSED


# -- Action methods ------------------------------------------------------------


def _patch_session(coordinator, sender):
    fake_session = type("S", (), {"get": sender})()
    coordinator.session = fake_session


@pytest.mark.asyncio
async def test_async_stop_calls_stop_endpoint(mock_coordinator, mock_entry):
    vac = _make_vacuum(mock_coordinator, mock_entry)
    sender, _ = make_post_mock()
    _patch_session(mock_coordinator, sender)
    await vac.async_stop()
    sender.assert_called_once_with("http://localhost:3000/api/local/action/stop")
    mock_coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_pause_calls_pause_endpoint(mock_coordinator, mock_entry):
    vac = _make_vacuum(mock_coordinator, mock_entry)
    sender, _ = make_post_mock()
    _patch_session(mock_coordinator, sender)
    await vac.async_pause()
    sender.assert_called_once_with("http://localhost:3000/api/local/action/pause")


@pytest.mark.asyncio
async def test_async_return_to_base_calls_dock_endpoint(mock_coordinator, mock_entry):
    vac = _make_vacuum(mock_coordinator, mock_entry)
    sender, _ = make_post_mock()
    _patch_session(mock_coordinator, sender)
    await vac.async_return_to_base()
    sender.assert_called_once_with("http://localhost:3000/api/local/action/dock")


@pytest.mark.asyncio
async def test_async_clean_spot_falls_back_to_start(mock_coordinator, mock_entry):
    vac = _make_vacuum(mock_coordinator, mock_entry)
    sender, _ = make_post_mock()
    _patch_session(mock_coordinator, sender)
    await vac.async_clean_spot()
    sender.assert_called_once_with("http://localhost:3000/api/local/action/start")


@pytest.mark.asyncio
async def test_async_start_uses_start_when_idle(mock_coordinator, mock_entry):
    vac = _make_vacuum(mock_coordinator, mock_entry)
    vac._attr_activity = VacuumActivity.IDLE
    sender, _ = make_post_mock()
    _patch_session(mock_coordinator, sender)
    await vac.async_start()
    sender.assert_called_once_with("http://localhost:3000/api/local/action/start")


@pytest.mark.asyncio
async def test_async_start_uses_resume_when_paused(mock_coordinator, mock_entry):
    vac = _make_vacuum(mock_coordinator, mock_entry)
    vac._attr_activity = VacuumActivity.PAUSED
    sender, _ = make_post_mock()
    _patch_session(mock_coordinator, sender)
    await vac.async_start()
    sender.assert_called_once_with("http://localhost:3000/api/local/action/resume")


@pytest.mark.asyncio
async def test_async_send_command_routes_known_commands(mock_coordinator, mock_entry):
    vac = _make_vacuum(mock_coordinator, mock_entry)
    sender, _ = make_post_mock()
    _patch_session(mock_coordinator, sender)
    await vac.async_send_command("dock")
    sender.assert_called_once_with("http://localhost:3000/api/local/action/dock")


@pytest.mark.asyncio
async def test_async_send_command_ignores_unknown_command(
    mock_coordinator, mock_entry
):
    vac = _make_vacuum(mock_coordinator, mock_entry)
    sender, _ = make_post_mock()
    _patch_session(mock_coordinator, sender)
    await vac.async_send_command("disco")
    sender.assert_not_called()
    mock_coordinator.async_request_refresh.assert_not_awaited()
