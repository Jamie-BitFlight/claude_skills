"""Direct unit tests for dh_core.operations.dispatch_stale_check / dispatch_conflicts.

Both functions previously had no direct test: the only existing coverage
(``test_frontend_parity_ops.py``'s CLI-forwarding test) fully mocks
``dh_core.operations.dispatch_stale_check``/``dispatch_conflicts`` rather than
calling the real implementation, so the ``UnsupportedBackendCapabilityError``
handling branch and its ``to_response()`` shape were unverified by any test.
``backlog_core.server``'s async MCP tools are thin ``asyncio.to_thread``
delegates to these same functions (T-P6-DEDUP), so exercising the real
functions here also covers the MCP boundary's failure path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import dh_core.operations as _dh_ops
import pytest
from backlog_core.backend_protocol import reset_config as _reset_bp_config, set_config as _set_bp_config
from backlog_core.backend_types import BacklogConfig as _BacklogConfig
from backlog_core.backends.sqlite_backend import SQLiteBackend

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def sqlite_backend():
    """Wire a real SQLiteBackend (supports_github_extras=False) as the active config."""
    _set_bp_config(_BacklogConfig(backend=SQLiteBackend(":memory:")))
    yield
    _reset_bp_config()


@pytest.mark.unit
def test_dispatch_stale_check_reports_capability_gap_on_non_github_backend(
    sqlite_backend: None, mocker: MockerFixture
) -> None:
    """dispatch_stale_check returns a structured capability-gap dict, not a crash.

    Why: this is the real function server.py now delegates to unchanged; a
         non-GitHub backend must produce UnsupportedBackendCapabilityError's
         to_response() shape, naming this specific operation.
    """
    mocker.patch("dh_core.operations._read_dispatch_plan", return_value=object())

    result = _dh_ops.dispatch_stale_check(milestone_number=42)

    assert result["unsupported_capability"] == "github_extras"
    assert result["backend"] == "SQLiteBackend"
    assert result["milestone_number"] == 42
    assert "dispatch_stale_check" in result["error"]


@pytest.mark.unit
def test_dispatch_conflicts_reports_capability_gap_on_non_github_backend(sqlite_backend: None) -> None:
    """dispatch_conflicts returns a structured capability-gap dict, not a crash.

    Why: same contract as dispatch_stale_check, exercised on the real function.
    """
    result = _dh_ops.dispatch_conflicts(milestone_number=42)

    assert result["unsupported_capability"] == "github_extras"
    assert result["backend"] == "SQLiteBackend"
    assert result["milestone_number"] == 42
    assert "dispatch_conflicts" in result["error"]
