"""Regression checks for the frustration-analyzer interpreter contract."""

from __future__ import annotations


def test_frustration_analyzer_server_imports_on_current_interpreter() -> None:
    """The MCP server module must import cleanly under the running interpreter.

    Replaces a prior version of this test that asserted the PEP 723
    ``requires-python`` bound equaled a literal string -- a tautology that
    proved only that the string was edited, not that the server actually
    works on the interpreters it claims to support. Reuses the existing
    ``_server`` loader from the plugin's own test suite (importable here
    via the shared ``pythonpath`` entry in the root ``pyproject.toml``)
    instead of duplicating its importlib boilerplate.
    """
    import _server

    assert _server.extract_user_messages is not None
