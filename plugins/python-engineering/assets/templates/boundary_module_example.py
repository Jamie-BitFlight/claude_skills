"""Boundary module example — the ONLY place Any is permitted in internal code."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IncomingRequest(BaseModel):
    """Validates raw external request data."""

    user_id: int = Field(gt=0)
    email: str = Field(pattern=r"^[\w.-]+@[\w.-]+\.\w+$")
    metadata: dict[str, str] = {}

    model_config = {"strict": True}


def parse_request(data: dict[str, Any]) -> IncomingRequest:
    """Convert raw dict to validated internal model.

    Any is permitted here because this is a boundary module.
    Downstream code receives IncomingRequest, not dict[str, Any].

    Returns:
        Validated IncomingRequest instance.
    """
    return IncomingRequest.model_validate(data)
