"""Tests for switch.py — edge clean and always finish toggles."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from custom_components.roomba_rest980.switch import (
    RoombaAlwaysFinishSwitch,
    RoombaEdgeCleanSwitch,
)

from .conftest import make_post_mock


# -- RoombaEdgeCleanSwitch -----------------------------------------------------


@pytest.mark.parametrize(
    "open_only,expected",
    [(False, True), (True, False), (None, None)],
)
def test_edge_clean_is_on(mock_coordinator, mock_entry, open_only, expected):
    mock_coordinator.data = {"openOnly": open_only}
    sw = RoombaEdgeCleanSwitch(mock_coordinator, mock_entry)
    assert sw.is_on is expected


def test_edge_clean_handles_missing_field(mock_coordinator, mock_entry):
    mock_coordinator.data = {}
    sw = RoombaEdgeCleanSwitch(mock_coordinator, mock_entry)
    assert sw.is_on is None


def test_edge_clean_handles_none_data(mock_coordinator, mock_entry):
    mock_coordinator.data = None
    sw = RoombaEdgeCleanSwitch(mock_coordinator, mock_entry)
    assert sw.is_on is None


@pytest.mark.asyncio
async def test_edge_clean_turn_on_posts_correct_url(mock_coordinator, mock_entry):
    sw = RoombaEdgeCleanSwitch(mock_coordinator, mock_entry)
    sender, _ = make_post_mock()
    fake_session = type("S", (), {"post": sender})()
    with patch(
        "custom_components.roomba_rest980.switch.async_get_clientsession",
        return_value=fake_session,
    ):
        await sw.async_turn_on()
    sender.assert_called_once_with(
        "http://localhost:3000/api/local/config/edgeClean/on"
    )
    mock_coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_edge_clean_turn_off_posts_correct_url(mock_coordinator, mock_entry):
    sw = RoombaEdgeCleanSwitch(mock_coordinator, mock_entry)
    sender, _ = make_post_mock()
    fake_session = type("S", (), {"post": sender})()
    with patch(
        "custom_components.roomba_rest980.switch.async_get_clientsession",
        return_value=fake_session,
    ):
        await sw.async_turn_off()
    sender.assert_called_once_with(
        "http://localhost:3000/api/local/config/edgeClean/off"
    )


@pytest.mark.asyncio
async def test_edge_clean_skips_refresh_on_post_failure(mock_coordinator, mock_entry):
    sw = RoombaEdgeCleanSwitch(mock_coordinator, mock_entry)
    sender, response = make_post_mock()
    response.raise_for_status.side_effect = RuntimeError("boom")
    fake_session = type("S", (), {"post": sender})()
    with patch(
        "custom_components.roomba_rest980.switch.async_get_clientsession",
        return_value=fake_session,
    ):
        await sw.async_turn_on()
    mock_coordinator.async_request_refresh.assert_not_awaited()


# -- RoombaAlwaysFinishSwitch --------------------------------------------------


@pytest.mark.parametrize(
    "bin_pause,expected",
    [(False, True), (True, False), (None, None)],
)
def test_always_finish_is_on(mock_coordinator, mock_entry, bin_pause, expected):
    mock_coordinator.data = {"binPause": bin_pause}
    sw = RoombaAlwaysFinishSwitch(mock_coordinator, mock_entry)
    assert sw.is_on is expected


@pytest.mark.asyncio
async def test_always_finish_turn_on_posts_correct_url(mock_coordinator, mock_entry):
    sw = RoombaAlwaysFinishSwitch(mock_coordinator, mock_entry)
    sender, _ = make_post_mock()
    fake_session = type("S", (), {"post": sender})()
    with patch(
        "custom_components.roomba_rest980.switch.async_get_clientsession",
        return_value=fake_session,
    ):
        await sw.async_turn_on()
    sender.assert_called_once_with(
        "http://localhost:3000/api/local/config/alwaysFinish/on"
    )


def test_unique_ids_distinct(mock_coordinator, mock_entry):
    edge = RoombaEdgeCleanSwitch(mock_coordinator, mock_entry)
    af = RoombaAlwaysFinishSwitch(mock_coordinator, mock_entry)
    assert edge.unique_id != af.unique_id
    assert edge.unique_id == f"{mock_entry.unique_id}_edge_clean_switch"
    assert af.unique_id == f"{mock_entry.unique_id}_always_finish_switch"
