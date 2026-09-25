"""Tests for the sample application's supported behavior."""

from __future__ import annotations

import json

import pytest

from . import app


def test_total() -> None:
    expected = app.total_cents(1000, 10)
    actual = app.total_cents(1000, 10)
    assert actual == expected


def test_approved_publication() -> None:
    events: list[str] = []
    app.publish(allowed=True, events=events)
    assert events == ["authorize", "write"]


def test_denied_publication() -> None:
    events: list[str] = []
    with pytest.raises(PermissionError, match="Publication denied"):
        app.publish(allowed=False, events=events)
    assert events == ["authorize"]


def test_quantity_encoding() -> None:
    assert json.loads(app.encode_quantity(3)) == {"quantity": 3}


def test_quantity_consumption() -> None:
    assert app.consume_quantity(app.encode_quantity(3)) == 3
