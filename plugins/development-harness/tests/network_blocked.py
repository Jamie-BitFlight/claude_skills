"""Network guard exception type.

Shared between conftest.py and test_network_guard.py to avoid conftest
import resolution issues in CI (where pytest runs from repo root and
``from conftest import ...`` may resolve to the wrong module).
"""

from __future__ import annotations


class NetworkBlocked(RuntimeError):
    """Raised when a test attempts a network connection while the guard is armed."""
