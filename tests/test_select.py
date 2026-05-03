"""Tests for select.py — carpet boost and cleaning passes selects."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from custom_components.roomba_rest980.select import (
    RoombaCarpetBoostSelect,
    RoombaCleaningPassesSelect,
)

from .conftest import make_post_mock


# -- RoombaCarpetBoostSelect ---------------------------------------------------


@pytest.mark.parametrize(
    "data,expected",
    [
        ({"carpetBoost": True, "vacHigh": False}, "Auto"),
        ({"carpetBoost": True, "vacHigh": True}, "Auto"),
        ({"carpetBoost": False, "vacHigh": True}, "Performance"),
        ({"carpetBoost": False, "vacHigh": False}, "Eco"),
        ({"carpetBoost": None, "vacHigh": False}, None),
        ({"carpetBoost": True, "vacHigh": None}, None),
        ({}, None),
    ],
)
def test_carpet_boost_current_option(mock_coordinator, mock_entry, data, expected):
    mock_coordinator.data = data
    sel = RoombaCarpetBoostSelect(mock_coordinator, mock_entry)
    assert sel.current_option == expected


def test_carpet_boost_handles_none_data(mock_coordinator, mock_entry):
    mock_coordinator.data = None
    sel = RoombaCarpetBoostSelect(mock_coordinator, mock_entry)
    assert sel.current_option is None


def test_carpet_boost_options_are_fixed(mock_coordinator, mock_entry):
    sel = RoombaCarpetBoostSelect(mock_coordinator, mock_entry)
    assert sel.options == ["Auto", "Performance", "Eco"]


@pytest.mark.parametrize(
    "option,expected_path",
    [
        ("Auto", "carpetBoost/auto"),
        ("Performance", "carpetBoost/performance"),
        ("Eco", "carpetBoost/eco"),
    ],
)
@pytest.mark.asyncio
async def test_carpet_boost_select_posts_correct_url(
    mock_coordinator, mock_entry, option, expected_path
):
    sel = RoombaCarpetBoostSelect(mock_coordinator, mock_entry)
    sender, _ = make_post_mock()
    fake_session = type("S", (), {"post": sender})()
    with patch(
        "custom_components.roomba_rest980.select.async_get_clientsession",
        return_value=fake_session,
    ):
        await sel.async_select_option(option)
    sender.assert_called_once_with(
        f"http://localhost:3000/api/local/config/{expected_path}"
    )
    mock_coordinator.async_request_refresh.assert_awaited_once()


# -- RoombaCleaningPassesSelect ------------------------------------------------


@pytest.mark.parametrize(
    "data,expected",
    [
        ({"noAutoPasses": False, "twoPass": False}, "Auto"),
        ({"noAutoPasses": False, "twoPass": True}, "Auto"),  # auto wins regardless
        ({"noAutoPasses": True, "twoPass": False}, "One"),
        ({"noAutoPasses": True, "twoPass": True}, "Two"),
        ({"noAutoPasses": None, "twoPass": False}, None),
        ({"noAutoPasses": True, "twoPass": None}, None),
        ({}, None),
    ],
)
def test_cleaning_passes_current_option(
    mock_coordinator, mock_entry, data, expected
):
    mock_coordinator.data = data
    sel = RoombaCleaningPassesSelect(mock_coordinator, mock_entry)
    assert sel.current_option == expected


@pytest.mark.parametrize(
    "option,expected_path",
    [
        ("Auto", "cleaningPasses/auto"),
        ("One", "cleaningPasses/one"),
        ("Two", "cleaningPasses/two"),
    ],
)
@pytest.mark.asyncio
async def test_cleaning_passes_select_posts_correct_url(
    mock_coordinator, mock_entry, option, expected_path
):
    sel = RoombaCleaningPassesSelect(mock_coordinator, mock_entry)
    sender, _ = make_post_mock()
    fake_session = type("S", (), {"post": sender})()
    with patch(
        "custom_components.roomba_rest980.select.async_get_clientsession",
        return_value=fake_session,
    ):
        await sel.async_select_option(option)
    sender.assert_called_once_with(
        f"http://localhost:3000/api/local/config/{expected_path}"
    )


def test_unique_ids_distinct(mock_coordinator, mock_entry):
    cb = RoombaCarpetBoostSelect(mock_coordinator, mock_entry)
    cp = RoombaCleaningPassesSelect(mock_coordinator, mock_entry)
    assert cb.unique_id != cp.unique_id
    assert cb.unique_id == f"{mock_entry.unique_id}_carpet_boost_select"
    assert cp.unique_id == f"{mock_entry.unique_id}_cleaning_passes_select"
