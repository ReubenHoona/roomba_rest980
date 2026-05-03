"""Tests for config_flow.py — URL normalization and JSON parsing."""

from __future__ import annotations

import pytest

from custom_components.roomba_rest980.config_flow import _normalize_base_url


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("http://localhost:3000", "http://localhost:3000"),
        ("http://localhost:3000/", "http://localhost:3000"),
        ("HTTP://localhost:3000", "http://localhost:3000"),
        ("HTTPS://Rest980/", "https://Rest980"),
        ("  http://rest980  ", "http://rest980"),
        ("rest980:3000", "rest980:3000"),  # no scheme, leave as-is
    ],
)
def test_normalize_base_url(raw, expected):
    assert _normalize_base_url(raw) == expected


def test_normalize_base_url_idempotent():
    once = _normalize_base_url("HTTP://Rest980/api/")
    twice = _normalize_base_url(once)
    assert once == twice
