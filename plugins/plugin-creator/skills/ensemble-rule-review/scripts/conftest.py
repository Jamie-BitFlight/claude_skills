"""Make the reducer script importable by its sibling test under any pytest import mode."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
