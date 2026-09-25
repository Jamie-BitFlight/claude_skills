"""Pricing, publication, and quantity serialization for the sample application."""

from __future__ import annotations

import json


def total_cents(net_cents: int, tax_percent: int) -> int:
    """Calculate an invoice total.

    Returns:
        Net cents plus tax rounded down to whole cents.
    """
    return net_cents + net_cents * tax_percent // 100


def publish(*, allowed: bool, events: list[str]) -> None:
    """Record authorization and publish when access is granted."""
    events.append("authorize")
    if not allowed:
        raise PermissionError("Publication denied")
    events.append("write")


def encode_quantity(quantity: int) -> str:
    """Encode a quantity for the consumer.

    Returns:
        A JSON object containing the quantity field.
    """
    return json.dumps({"quantity": quantity})


def consume_quantity(wire: str) -> int:
    """Read the consumer's quantity field.

    Returns:
        The quantity decoded from the wire representation.
    """
    return int(json.loads(wire)["quantity"])
