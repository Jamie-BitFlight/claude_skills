"""Format-specific readers for SAM task/plan files.

Each reader converts a specific file format into raw dicts suitable for
normalization by ``readers.normalize``. No Pydantic model construction
happens inside readers — that is the normalizer's responsibility.
"""

from __future__ import annotations
