"""A misconfigured backend name must not leave ``create_backend`` as a bare ``ValueError``.

``create_backend`` resolves its name from ``BACKLOG_BACKEND``, then ``.dh/config.yaml``,
then the beads marker, and refuses a name it does not recognise. The refusal was a plain
``ValueError``. Every MCP tool reaches it: they all call ``get_config().backend.X(...)``,
and ``get_config`` builds the singleton by calling ``create_backend()``. The tool
wrappers catch ``BacklogError``, so a typo in the env var or the config file failed the
tool call with an unhandled exception instead of the documented ``error`` field.

Same defect, same fix as d0f7bee87: raise ``ValidationError``, a ``BacklogError``
subclass. ``backend_protocol`` already imports from ``models`` (``ContentConflictError``
and four siblings), so the import adds no cycle -- the module docstring's dependency
direction ``models <- backend_protocol`` is unchanged.
"""

from __future__ import annotations

import pytest
from backlog_core import operations
from backlog_core.backend_protocol import reset_config
from backlog_core.models import BacklogError


@pytest.mark.unit
def test_unknown_backend_name_refuses_as_a_backlog_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """``operations.try_get_github`` is the shortest MCP-reachable path through ``get_config``.

    Every other tool entry point reaches the same factory the same way.
    """
    monkeypatch.setenv("BACKLOG_BACKEND", "not-a-real-backend")
    reset_config()
    try:
        with pytest.raises(BacklogError, match="Unknown backend"):
            operations.try_get_github()
    finally:
        reset_config()
