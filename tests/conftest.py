"""Shared fixtures for roomba_rest980 tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Allow `import custom_components.roomba_rest980...`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def mock_entry():
    """A minimal config entry stand-in."""
    entry = MagicMock()
    entry.unique_id = "abcd1234"
    entry.title = "Roomba"
    entry.entry_id = "test_entry_id"
    entry.data = {"base_url": "http://localhost:3000", "cloud_api": False}
    entry.runtime_data = MagicMock()
    return entry


@pytest.fixture
def mock_coordinator():
    """A coordinator with controllable .data and async refresh."""
    coord = MagicMock()
    coord.data = {}
    coord.async_request_refresh = AsyncMock()
    coord.session = MagicMock()
    coord.url = "http://localhost:3000"
    coord.async_add_listener = MagicMock(return_value=lambda: None)
    return coord


def make_post_mock(status: int = 200):
    """Build a context-manager mock that imitates `session.post()` / `.get()`."""
    response = MagicMock()
    response.status = status
    response.raise_for_status = MagicMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=None)

    sender = MagicMock(return_value=cm)
    return sender, response
