"""sam_schema: Unified SAM task/plan schema module.

Single shared Python package for reading, writing, and querying SAM task/plan
files. Replaces the five independent parsers in the SAM pipeline with a single
interface backed by validated Pydantic models.

Public API
----------
The following names are re-exported at the package level.

Models:

    Plan, Task, TaskStatus, Complexity, Priority, SchemaGap, ReadResult, PlanStatus

Query layer:

    load_plan, get_task, list_tasks, get_ready_tasks, update_status, get_plan_status

Format detection:

    detect_format, FormatType

Writer:

    write_plan
"""

from __future__ import annotations

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
from sam_schema.core.query import (
    claim_task,
    get_plan_status,
    get_ready_tasks,
    get_task,
    list_tasks,
    load_plan,
    update_status,
)
from sam_schema.readers.detect import FormatType, detect_format
from sam_schema.writers.yaml_writer import write_plan

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
    "FormatType",
    "IssueClassification",
    "Plan",
    "PlanStatus",
    "Priority",
    "ReadResult",
    "SchemaGap",
    "Task",
    "TaskStatus",
    "claim_task",
    "detect_format",
    "get_plan_status",
    "get_ready_tasks",
    "get_task",
    "list_tasks",
    "load_plan",
    "update_status",
    "write_plan",
]
