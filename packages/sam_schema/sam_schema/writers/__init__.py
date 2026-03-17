"""Writers for SAM task/plan files.

The canonical write format is pure YAML. Writers use ``ruamel.yaml`` in
round-trip mode to preserve comments and field order on read-modify-write cycles.
"""

from __future__ import annotations
