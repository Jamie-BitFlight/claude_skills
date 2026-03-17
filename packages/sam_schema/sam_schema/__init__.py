"""sam_schema: Unified SAM task/plan schema module.

Single shared Python package for reading, writing, and querying SAM task/plan
files. Replaces the five independent parsers in the SAM pipeline with a single
interface backed by validated Pydantic models.

Public API
----------
The following names are re-exported at the package level. Downstream modules
(readers, writers, query layer) are imported lazily so this ``__init__.py``
does not raise ``NotImplementedError`` at import time when stubs are active.

Models (always available):

    Plan, Task, TaskStatus, Complexity, Priority, SchemaGap, ReadResult, PlanStatus

Query layer (available after T7 — query.py implementation):

    load_plan, get_task, list_tasks, get_ready_tasks, update_status, get_plan_status

Format detection (available after T2 — readers implementation):

    detect_format, FormatType

Writer (available after T3 — writer implementation):

    write_plan
"""

from __future__ import annotations

import importlib

# Models are always available — no downstream stubs required.
from sam_schema.core.dependencies import BookendValidator
from sam_schema.core.models import (
    STATUS_MAP,
    TASK_ID_PATTERN,
    AcceptanceCriterion,
    AnalysisMethod,
    BookendResult,
    BookendType,
    BookendVerification,
    Complexity,
    CriterionStatus,
    IssueClassification,
    Plan,
    PlanStatus,
    Priority,
    ReadResult,
    SchemaGap,
    Task,
    TaskStatus,
)

__all__ = [
    "STATUS_MAP",
    "TASK_ID_PATTERN",
    "AcceptanceCriterion",
    "AnalysisMethod",
    "BookendResult",
    "BookendType",
    "BookendValidator",
    "BookendVerification",
    "Complexity",
    "CriterionStatus",
    "IssueClassification",
    "Plan",
    "PlanStatus",
    "Priority",
    "ReadResult",
    "SchemaGap",
    "Task",
    "TaskStatus",
]

# Lazy imports for downstream components that are stubs until their tasks complete.
# Each import is guarded so that a NotImplementedError from the stub body does NOT
# propagate at module import time. Callers that need these names import them directly.


def __getattr__(name: str) -> object:
    """Lazy import for query, reader, and writer symbols not yet implemented.

    Args:
        name: Attribute name being accessed on this module.

    Returns:
        The requested module-level symbol.

    Raises:
        AttributeError: If ``name`` is not a known public symbol.
    """
    lazy_map: dict[str, tuple[str, str]] = {
        "load_plan": ("sam_schema.core.query", "load_plan"),
        "get_task": ("sam_schema.core.query", "get_task"),
        "list_tasks": ("sam_schema.core.query", "list_tasks"),
        "get_ready_tasks": ("sam_schema.core.query", "get_ready_tasks"),
        "update_status": ("sam_schema.core.query", "update_status"),
        "get_plan_status": ("sam_schema.core.query", "get_plan_status"),
        "claim_task": ("sam_schema.core.query", "claim_task"),
        "detect_format": ("sam_schema.readers.detect", "detect_format"),
        "FormatType": ("sam_schema.readers.detect", "FormatType"),
        "write_plan": ("sam_schema.writers.yaml_writer", "write_plan"),
    }

    if name in lazy_map:
        module_path, attr = lazy_map[name]
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)

    msg = f"module 'sam_schema' has no attribute '{name}'"
    raise AttributeError(msg)
