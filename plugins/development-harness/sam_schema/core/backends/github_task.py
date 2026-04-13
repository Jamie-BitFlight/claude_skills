"""GitHubTaskProvider — SAM TaskBackend composing IssueBackend + DocumentBackend.

Maps SAM primitives to GitHub primitives:

- Plans   → GitHub Issues with label ``sam:plan``
- Tasks   → Sub-issues titled ``[T{id}] {title}`` with label ``sam:{status}``
- Status  → Label swap among ``sam:not-started`` … ``sam:skipped``
- Docs    → Delegated to DocumentBackend (TODO: replace stub with #984 impl)

All GitHub operations go through the IssueBackend Protocol; no direct REST
or GraphQL calls are made from this module.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from sam_schema.core.backends._utils import _now_iso, validate_appended_task
from sam_schema.core.dependencies import TERMINAL_STATUSES as _TERMINAL_STATUSES
from sam_schema.core.exceptions import PlanNotFoundError, TaskNotFoundError, TaskValidationError
from sam_schema.core.models import PlanState, Task
from sam_schema.core.task_backend_types import DocumentData, DocumentHandle, PlanData, PlanSummary, TaskData

if TYPE_CHECKING:
    from collections.abc import Sequence

    from backlog_core.backend_protocol import BacklogBackend, IssueNode, LabelNode
    from github.Repository import Repository

__all__ = ["DocumentBackend", "GitHubTaskProvider"]

# TODO(#984): Remove DocumentBackend stub and import from canonical location once #984 delivers.


@runtime_checkable
class DocumentBackend(Protocol):
    """Minimal Protocol for document storage (stub pending issue #984)."""

    def store_document(
        self, plan_id: str, task_id: str | None, stage: str, doc_type: str, title: str, content: str, fmt: str = "md"
    ) -> DocumentHandle:
        """Store a document and return an opaque handle."""
        ...

    def read_document(self, handle: DocumentHandle) -> DocumentData:
        """Retrieve a stored document by its handle."""
        ...


_SAM_PLAN_LABEL = "sam:plan"
_SAM_TASK_LABEL = "sam:task"

_STATUS_TO_LABEL: dict[str, str] = {
    "not-started": "sam:not-started",
    "in-progress": "sam:in-progress",
    "complete": "sam:complete",
    "blocked": "sam:blocked",
    "deferred": "sam:deferred",
    "skipped": "sam:skipped",
}
_LABEL_TO_STATUS: dict[str, str] = {v: k for k, v in _STATUS_TO_LABEL.items()}
_METADATA_BEGIN = "<!-- sam-task-metadata:begin -->"
_METADATA_END = "<!-- sam-task-metadata:end -->"
_META_ROW_RE = re.compile(r"^\|\s*(?P<key>[^|]+?)\s*\|\s*(?P<value>[^|]*?)\s*\|$")
_TASK_TITLE_RE = re.compile(r"^\[(?P<tid>T\d+)\] (?P<title>.+)$")
_PLAN_SLUG_RE = re.compile(r"<!-- sam-plan-slug: (?P<slug>[^>]+?) -->")
_DRAFTING_MARKER = "<!-- sam:state=drafting -->"
_GOAL_RE = re.compile(r"## Goal\n\n(?P<goal>.+?)(?=\n\n##|\Z)", re.DOTALL)


def _status_from_labels(labels: list[LabelNode]) -> str:
    """Extract the SAM status string from a list of label dicts."""
    for lbl in labels:
        name = lbl.get("name", "")
        if name in _LABEL_TO_STATUS:
            return _LABEL_TO_STATUS[name]
    return "not-started"


def _render_metadata_section(task: Task, plan_id: str) -> str:
    """Render the ``<!-- sam-task-metadata:begin/end -->`` table block."""
    # Use model_dump to get Python-native values (enum members, not raw strings)
    td = task.model_dump(mode="python", by_alias=False)
    rows: list[tuple[str, str]] = [
        ("task_id", td["id"]),
        ("plan_id", plan_id),
        ("agent", td.get("agent") or ""),
        ("priority", str(td.get("priority", 0))),
        ("complexity", str(td.get("complexity", ""))),
        ("dependencies", ",".join(td.get("dependencies") or [])),
        ("skills", ",".join(td.get("skills") or [])),
        ("created", str(td.get("created") or _now_iso())),
        ("started", str(td.get("started") or "")),
        ("completed", str(td.get("completed") or "")),
    ]
    lines = [_METADATA_BEGIN, "| Field | Value |", "|-------|-------|"]
    lines.extend(f"| {k} | {v} |" for k, v in rows)
    lines.append(_METADATA_END)
    return "\n".join(lines)


def _parse_metadata(body: str) -> dict[str, str]:
    """Parse the sam-task-metadata table from an issue body."""
    begin = body.find(_METADATA_BEGIN)
    end = body.find(_METADATA_END)
    if begin == -1 or end == -1:
        return {}
    section = body[begin + len(_METADATA_BEGIN) : end]
    result: dict[str, str] = {}
    for line in section.splitlines():
        m = _META_ROW_RE.match(line)
        if m:
            key = m.group("key").strip()
            if key not in {"Field", "-------"}:
                result[key] = m.group("value").strip()
    return result


def _render_plan_body(slug: str, goal: str, context: str | None, ac: str | None) -> str:
    """Render the parent plan issue body."""
    parts = [f"## Goal\n\n{goal}"]
    if context:
        parts.append(f"## Context\n\n{context}")
    if ac:
        parts.append(f"## Acceptance Criteria\n\n{ac}")
    parts.append(f"<!-- sam-plan-slug: {slug} -->")
    return "\n\n".join(parts)


def _render_task_body(task: Task, plan_id: str) -> str:
    """Render the full sub-issue body for a task."""
    parts = [_render_metadata_section(task, plan_id)]
    if task.body:
        parts.append(task.body)
    if task.acceptance_criteria:
        parts.append(f"## Acceptance Criteria\n\n{task.acceptance_criteria}")
    if task.verification_steps:
        parts.append(f"## Verification Steps\n\n{task.verification_steps}")
    return "\n\n".join(parts)


def _node_to_task_data(node: IssueNode) -> TaskData:
    """Convert an IssueNode to a TaskData TypedDict."""
    m = _TASK_TITLE_RE.match(node["title"])
    meta = _parse_metadata(node["body"])
    task_id = meta.get("task_id") or (m.group("tid") if m else str(node["number"]))
    title = m.group("title") if m else node["title"]
    deps = [d.strip() for d in meta.get("dependencies", "").split(",") if d.strip()]
    skills = [s.strip() for s in meta.get("skills", "").split(",") if s.strip()]
    return TaskData(
        id=task_id,
        title=title,
        status=_status_from_labels(node["labels"]),
        agent=meta.get("agent") or None,
        dependencies=deps,
        blocked_by=[],
        parallelize_with=[],
        priority=int(meta.get("priority") or 0),
        complexity=meta.get("complexity", ""),
        skills=skills,
        created=meta.get("created") or node["createdAt"],
        started=meta.get("started") or None,
        completed=meta.get("completed") or None,
        last_activity=node["updatedAt"],
        body=node["body"],
        description="",
    )


def _is_ready(task: TaskData, by_id: dict[str, TaskData]) -> bool:
    """Return True when a task is not-started and all dependencies are terminal."""
    if task["status"] != "not-started":
        return False
    return all(by_id.get(dep, {}).get("status") in _TERMINAL_STATUSES for dep in task["dependencies"])  # type: ignore[union-attr]


def _has_cycles(tasks: list[TaskData]) -> bool:
    """Return True when the dependency graph contains a cycle (DFS three-colour)."""
    adj: dict[str, list[str]] = {t["id"]: list(t["dependencies"]) for t in tasks}
    colour: dict[str, int] = dict.fromkeys(adj, 0)

    def dfs(node: str) -> bool:
        colour[node] = 1
        for dep in adj.get(node, []):
            if dep not in colour:
                continue
            if colour[dep] == 1:
                return True
            if colour[dep] == 0 and dfs(dep):
                return True
        colour[node] = 2
        return False

    return any(colour[n] == 0 and dfs(n) for n in list(adj))


def _rebuild_metadata_body(node: IssueNode, meta: dict[str, str]) -> str:
    """Replace the metadata section in a body with updated key-value pairs."""
    rows = ["| Field | Value |", "|-------|-------|"]
    rows.extend(f"| {k} | {v} |" for k, v in meta.items())
    new_section = "\n".join([_METADATA_BEGIN, *rows, _METADATA_END])
    body = node["body"]
    begin = body.find(_METADATA_BEGIN)
    end = body.find(_METADATA_END)
    if begin != -1 and end != -1:
        return body[:begin] + new_section + body[end + len(_METADATA_END) :]
    return new_section + "\n\n" + body


class GitHubTaskProvider:
    """SAM TaskBackend that stores plans and tasks as GitHub Issues.

    - Plans map to GitHub Issues labelled ``sam:plan``.
    - Tasks map to sub-issues titled ``[T{id}] {title}`` labelled ``sam:{status}``.
    - The ``plan_id`` returned by this backend is the GitHub issue number (str).

    Args:
        issue_backend: BacklogBackend providing GitHub Issue operations.
        doc_backend: DocumentBackend for document storage (stub pending #984).
    """

    def __init__(self, issue_backend: BacklogBackend, doc_backend: DocumentBackend) -> None:
        """Store the IssueBackend and DocumentBackend dependency instances."""
        self._issue_backend = issue_backend
        self._doc_backend = doc_backend
        # Per-plan task-ID cache — avoids O(N²) sub-issue fetches during
        # incremental append_task workflows.  Keyed by plan_id (str).
        # Populated lazily on first append_task call per plan; invalidated on
        # finalize_plan to force a fresh read if the plan is re-used.
        self._task_id_cache: dict[str, set[str]] = {}

    def _get_repo(self) -> tuple[Repository, str, str]:
        """Return (repo, owner, repo_name) from the IssueBackend."""
        repo = self._issue_backend.get_github()
        owner: str = repo.owner.login  # type: ignore[attr-defined]
        name: str = repo.name  # type: ignore[attr-defined]
        return repo, owner, name  # type: ignore[return-value]

    def _fetch_plan_node(self, plan_id: str) -> IssueNode:
        """Fetch the parent plan issue node; raise PlanNotFoundError if absent."""
        try:
            issue_number = int(plan_id)
        except ValueError:
            raise PlanNotFoundError(plan_id) from None
        repo, owner, name = self._get_repo()
        node = self._issue_backend._fetch_issue_graphql(repo, owner, name, issue_number)  # type: ignore[arg-type]
        if _SAM_PLAN_LABEL not in [lbl["name"] for lbl in node["labels"]]:  # type: ignore[index]
            raise PlanNotFoundError(plan_id)
        return node

    def _fetch_task_nodes(self, plan_id: str) -> list[IssueNode]:
        """Fetch all task sub-issues for a plan."""
        try:
            parent_number = int(plan_id)
        except ValueError:
            raise PlanNotFoundError(plan_id) from None
        repo, _, _ = self._get_repo()
        return self._issue_backend.get_task_issues(repo, parent_number)  # type: ignore[arg-type, return-value]

    def _find_task_node(self, plan_id: str, task_id: str) -> IssueNode:
        """Locate a specific task sub-issue; raise TaskNotFoundError if absent."""
        for node in self._fetch_task_nodes(plan_id):
            m = _TASK_TITLE_RE.match(node["title"])
            if (m and m.group("tid") == task_id) or _parse_metadata(node["body"]).get("task_id") == task_id:
                return node
        raise TaskNotFoundError(plan_id, task_id)

    def _extract_plan_meta(self, node: IssueNode) -> tuple[str, str]:
        """Return (slug, goal) parsed from a plan issue body."""
        body = node["body"]
        slug_m = _PLAN_SLUG_RE.search(body)
        slug = slug_m.group("slug").strip() if slug_m else node["title"].removeprefix("SAM Plan: ")
        goal_m = _GOAL_RE.search(body)
        return slug, goal_m.group("goal").strip() if goal_m else ""

    def create_plan(
        self,
        slug: str,
        goal: str,
        tasks: Sequence[Task],
        *,
        context: str | None = None,
        issue: int | None = None,
        acceptance_criteria: str | None = None,
    ) -> PlanData:
        """Create a plan as a parent GitHub Issue with task sub-issues."""
        for i, task in enumerate(tasks):
            if not task.id or not task.title:
                raise TaskValidationError(i, "Task must have 'id' and 'title' fields")

        repo, _, _ = self._get_repo()
        plan_body = _render_plan_body(slug, goal, context, acceptance_criteria)
        if not tasks:
            plan_body = f"{plan_body}\n{_DRAFTING_MARKER}"
        parent_issue = repo.create_issue(  # type: ignore[attr-defined]
            title=f"SAM Plan: {slug}", body=plan_body, labels=[_SAM_PLAN_LABEL]
        )
        plan_id = str(parent_issue.number)  # type: ignore[attr-defined]

        task_data_list: list[TaskData] = []
        for task in tasks:
            task_body = _render_task_body(task, plan_id)
            status_label = _STATUS_TO_LABEL.get(str(task.status), "sam:not-started")
            task_issue = repo.create_issue(  # type: ignore[attr-defined]
                title=f"[{task.id}] {task.title}", body=task_body, labels=[_SAM_TASK_LABEL, status_label]
            )
            task_data_list.append(
                TaskData(
                    id=task.id,
                    title=task.title,
                    status=str(task.status),
                    agent=task.agent or None,
                    dependencies=task.dependencies or [],
                    blocked_by=task.blocked_by or [],
                    parallelize_with=task.parallelize_with or [],
                    priority=int(task.priority),
                    complexity=str(task.complexity),
                    skills=task.skills or [],
                    created=_now_iso(),
                    started=None,
                    completed=None,
                    last_activity=_now_iso(),
                    body=task_body,
                    description="",
                    github_issue=task_issue.number,  # type: ignore[attr-defined]
                )
            )

        return PlanData(
            plan_id=plan_id,
            feature=slug,
            version="1",
            description=goal,
            goal=goal,
            context=context or "",
            acceptance_criteria=acceptance_criteria or "",
            issue=str(issue) if issue else None,
            tasks=task_data_list,
            source_path=None,
        )

    def read_plan(self, plan_id: str) -> PlanData:
        """Fetch the plan issue and all task sub-issues."""
        node = self._fetch_plan_node(plan_id)
        slug, goal = self._extract_plan_meta(node)
        tasks = [_node_to_task_data(n) for n in self._fetch_task_nodes(plan_id)]
        plan_data = PlanData(
            plan_id=plan_id,
            feature=slug,
            version="1",
            description=goal,
            goal=goal,
            context="",
            acceptance_criteria="",
            issue=None,
            tasks=tasks,
            source_path=None,
        )
        if _DRAFTING_MARKER in (node.get("body") or ""):
            plan_data["state"] = PlanState.DRAFTING
        return plan_data

    def list_plans(self, *, search: str | None = None, offset: int = 0, limit: int | None = None) -> list[PlanSummary]:
        """List all SAM plan issues, optionally filtered by search substring."""
        repo, owner, name = self._get_repo()
        nodes = self._issue_backend._fetch_issues_graphql(  # type: ignore[arg-type]
            repo, owner, name, state="OPEN", labels=[_SAM_PLAN_LABEL]
        )
        summaries: list[PlanSummary] = []
        for node in nodes:
            slug, goal = self._extract_plan_meta(node)
            if search and search.lower() not in slug.lower() and search.lower() not in goal.lower():
                continue
            task_count = len(self._issue_backend.get_task_issues(repo, node["number"]))  # type: ignore[arg-type]
            summaries.append(
                PlanSummary(
                    plan_id=str(node["number"]),
                    feature=slug,
                    goal=goal,
                    description=goal,
                    task_count=task_count,
                    source_path=None,
                )
            )
        summaries.sort(key=lambda s: int(s["plan_id"]))
        end = offset + limit if limit is not None else None
        return summaries[offset:end]

    def update_plan_fields(
        self, plan_id: str, *, context: str | None = None, set_fields: dict[str, str | int | list[str]] | None = None
    ) -> None:
        """Update top-level fields on a plan issue body."""
        node = self._fetch_plan_node(plan_id)
        body = node["body"]
        if context:
            ctx_block = f"## Context\n\n{context}"
            ctx_start = body.find("## Context\n\n")
            if ctx_start != -1:
                next_sec = body.find("\n## ", ctx_start + 1)
                body = (body[:ctx_start] + ctx_block) + ("\n\n" + body[next_sec + 1 :] if next_sec != -1 else "")
            else:
                slug_pos = body.find("<!-- sam-plan-slug:")
                body = (
                    (body[:slug_pos] + ctx_block + "\n\n" + body[slug_pos:])
                    if slug_pos != -1
                    else (body + "\n\n" + ctx_block)
                )
        repo, _, _ = self._get_repo()
        self._issue_backend._update_issue_graphql(repo, node["id"], body=body)  # type: ignore[arg-type]

    def read_task(self, plan_id: str, task_id: str) -> TaskData:
        """Fetch a single task sub-issue."""
        self._fetch_plan_node(plan_id)
        return _node_to_task_data(self._find_task_node(plan_id, task_id))

    def claim_task(self, plan_id: str, task_id: str) -> bool:
        """Transition task from not-started → in-progress; return False if not claimable."""
        self._fetch_plan_node(plan_id)
        node = self._find_task_node(plan_id, task_id)
        if _status_from_labels(node["labels"]) != "not-started":
            return False
        repo, _, _ = self._get_repo()
        self._issue_backend.update_task_status(repo, node["number"], "in-progress")  # type: ignore[arg-type]
        return True

    def update_task_status(self, plan_id: str, task_id: str, status: str) -> None:
        """Swap the SAM status label on a task sub-issue."""
        if status not in _STATUS_TO_LABEL:
            raise TaskValidationError(0, f"Invalid status {status!r}; valid: {sorted(_STATUS_TO_LABEL)}")
        self._fetch_plan_node(plan_id)
        node = self._find_task_node(plan_id, task_id)
        repo, _, _ = self._get_repo()
        self._issue_backend.update_task_status(repo, node["number"], status)  # type: ignore[arg-type]

    def update_task_fields(self, plan_id: str, task_id: str, fields: dict[str, str | int | list[str]]) -> None:
        """Update scalar fields in the task sub-issue metadata table."""
        self._fetch_plan_node(plan_id)
        node = self._find_task_node(plan_id, task_id)
        meta = _parse_metadata(node["body"])
        for key, value in fields.items():
            meta[key] = ",".join(str(v) for v in value) if isinstance(value, list) else str(value)
        new_body = _rebuild_metadata_body(node, meta)
        repo, _, _ = self._get_repo()
        self._issue_backend._update_issue_graphql(repo, node["id"], body=new_body)  # type: ignore[arg-type]

    def append_task_section(self, plan_id: str, task_id: str, section_name: str, content: str) -> None:
        """Append markdown content to a named section of a task body."""
        self._fetch_plan_node(plan_id)
        node = self._find_task_node(plan_id, task_id)
        heading = f"## {section_name}"
        new_body = node["body"] + (f"\n\n{content}" if heading in node["body"] else f"\n\n{heading}\n\n{content}")
        repo, _, _ = self._get_repo()
        self._issue_backend._update_issue_graphql(repo, node["id"], body=new_body)  # type: ignore[arg-type]

    def get_ready_tasks(self, plan_id: str) -> list[TaskData]:
        """Return tasks whose status is not-started and all dependencies are terminal."""
        self._fetch_plan_node(plan_id)
        tasks = [_node_to_task_data(n) for n in self._fetch_task_nodes(plan_id)]
        by_id: dict[str, TaskData] = {t["id"]: t for t in tasks}
        return [t for t in tasks if _is_ready(t, by_id)]

    def get_plan_status(self, plan_id: str) -> dict[str, object]:
        """Return a summary dict of task status counts for a plan."""
        node = self._fetch_plan_node(plan_id)
        slug, _ = self._extract_plan_meta(node)
        # Derive plan state from drafting marker in the issue body.
        state = PlanState.DRAFTING if _DRAFTING_MARKER in (node.get("body") or "") else PlanState.READY
        tasks = [_node_to_task_data(n) for n in self._fetch_task_nodes(plan_id)]
        by_id: dict[str, TaskData] = {t["id"]: t for t in tasks}
        by_status: dict[str, int] = {}
        for t in tasks:
            by_status[t["status"]] = by_status.get(t["status"], 0) + 1
        ready = [t["id"] for t in tasks if _is_ready(t, by_id)]
        blocked: list[dict[str, list[str]]] = []
        for t in tasks:
            if t["status"] == "not-started" and not _is_ready(t, by_id) and t["dependencies"]:
                unmet = [d for d in t["dependencies"] if by_id.get(d, {}).get("status") not in _TERMINAL_STATUSES]  # type: ignore[union-attr]
                if unmet:
                    blocked.append({t["id"]: unmet})
        completed = by_status.get("complete", 0)
        pct = (completed / len(tasks) * 100.0) if tasks else 0.0
        return {
            "feature": slug,
            "total_tasks": len(tasks),
            "by_status": by_status,
            "ready_tasks": ready,
            "blocked_tasks": blocked,
            "completion_pct": pct,
            "has_cycles": _has_cycles(tasks),
            "state": state,
        }

    def append_task(self, plan_id: str, task: Task) -> dict[str, Any]:
        """Append a single validated Task to an existing plan as a GitHub sub-issue.

        Duplicate-ID check via ``validate_appended_task``; see ADR-1770-1 for the
        single-writer contract (callers must serialise writes to the same plan).

        Args:
            plan_id: Plan identifier (GitHub issue number string).
            task: Validated Task model to append.

        Returns:
            Dict with ``appended`` (True), ``task_id`` (str), and ``github_issue`` (int).

        Raises:
            PlanNotFoundError: When plan_id does not correspond to a SAM plan issue.
            TaskValidationError: When the task ID already exists in the plan.
        """
        self._fetch_plan_node(plan_id)

        # Populate cache on first call per plan, then reuse — eliminates O(N²)
        # GitHub API calls when appending N tasks in sequence.
        if plan_id not in self._task_id_cache:
            fetched: set[str] = set()
            for n in self._fetch_task_nodes(plan_id):
                meta_id = _parse_metadata(n["body"]).get("task_id")
                if meta_id:
                    fetched.add(meta_id)
                else:
                    m = _TASK_TITLE_RE.match(n["title"])
                    if m:
                        fetched.add(m.group("tid"))
            self._task_id_cache[plan_id] = fetched

        validate_appended_task(task, self._task_id_cache[plan_id], plan_id)
        self._task_id_cache[plan_id].add(task.id)

        task_body = _render_task_body(task, plan_id)
        status_val = str(task.status)
        status_label = _STATUS_TO_LABEL.get(status_val, "sam:not-started")
        repo, _, _ = self._get_repo()
        task_issue = repo.create_issue(  # type: ignore[attr-defined]
            title=f"[{task.id}] {task.title}", body=task_body, labels=[_SAM_TASK_LABEL, status_label]
        )

        return {"appended": True, "task_id": task.id, "github_issue": task_issue.number}  # type: ignore[attr-defined]

    def finalize_plan(self, plan_id: str) -> dict[str, Any]:
        """Transition a plan from drafting state to ready state.

        Clears the ``<!-- sam:state=drafting -->`` marker from the issue body.
        See ADR-1770-1 for the single-writer contract (callers must serialise
        writes to the same plan).

        Args:
            plan_id: Plan identifier (GitHub issue number string).

        Returns:
            Dict with ``finalized`` (True) and ``state`` ("ready").

        Raises:
            PlanNotFoundError: When plan_id does not correspond to a SAM plan issue.
        """
        node = self._fetch_plan_node(plan_id)
        body = node["body"]
        # No-op guard: already ready — drafting marker absent, nothing to write.
        if _DRAFTING_MARKER not in body:
            return {"finalized": True, "state": PlanState.READY}
        new_body = re.sub(r"\n?" + re.escape(_DRAFTING_MARKER), "", body)
        repo, _, _ = self._get_repo()
        self._issue_backend._update_issue_graphql(repo, node["id"], body=new_body)  # type: ignore[arg-type]
        # Invalidate task-ID cache so subsequent reads pick up the current state.
        self._task_id_cache.pop(plan_id, None)
        return {"finalized": True, "state": PlanState.READY}

    def store_document(
        self, plan_id: str, task_id: str | None, stage: str, doc_type: str, title: str, content: str, fmt: str = "md"
    ) -> DocumentHandle:
        """Delegate document storage to DocumentBackend."""
        self._fetch_plan_node(plan_id)
        return self._doc_backend.store_document(plan_id, task_id, stage, doc_type, title, content, fmt)

    def read_document(self, handle: DocumentHandle) -> DocumentData:
        """Delegate document retrieval to DocumentBackend."""
        return self._doc_backend.read_document(handle)
