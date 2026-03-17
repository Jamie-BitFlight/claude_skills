# SAM Task Parsing Patterns

**Analysis Date:** 2026-03-14
**Focus:** Task file parsing architecture, patterns, and integration points

---

## 1. Parser Architecture Overview

The codebase implements a multi-layer parsing strategy supporting **three task file formats**:

1. **YAML Frontmatter Single File** — one `.md` file containing multiple `---`-delimited task sections
2. **YAML Frontmatter Directory** — one `.md` file per task in a `tasks-{slug}/` directory
3. **Legacy Markdown** (deprecated) — regex-based parsing of `## Task N: Title` headers with `**Status**: ...` metadata

**Primary Parser:** `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py:547` (`parse_task_file()`)

**Supporting Utilities:** `plugins/python3-development/skills/implementation-manager/scripts/task_format.py`

**Legacy Migration:** `plugins/python3-development/scripts/migrate_task_format.py`

---

## 2. Format Expectations by Parser

### 2.1 YAML Frontmatter Detection

**Location:** `task_format.py:103-129` (`has_yaml_frontmatter()`)

**What it detects:**
```python
def has_yaml_frontmatter(content: str) -> bool:
    if not content or not content.startswith(_FRONTMATTER_DELIMITER):
        return False
    closing_idx = content.find("\n---\n", len(_FRONTMATTER_DELIMITER))
    # Must have both opening AND closing delimiters
```

**Expected format:**
```markdown
---
task: T1
title: Task Title
status: not-started
---

## Body content here
```

**Key constraint:** File must START with `---\n` on line 1. No content before first delimiter.

**Failure case:** Fenced YAML (code blocks with triple-backticks) is detected but treated as malformed:
```markdown
```yaml
---
task: T1
---
```
```
This will fail — the outer backticks hide the `---` delimiters from the parser.

---

### 2.2 YAML Frontmatter Parsing

**Location:** `task_format.py:132-171` (`parse_yaml_frontmatter()`)

**Steps:**
1. Split content on `---\n` delimiter (exactly 3 parts expected: empty prefix, YAML block, body)
2. Parse YAML block using `ruamel.yaml` (NOT `pyyaml`)
3. Validate result is a dict (not a list or scalar)
4. Return tuple: `(frontmatter_dict, body_string)`

**Parsed dict example:**
```python
{
    'task': 'T1',
    'title': 'Create Data Models',
    'status': 'not-started',
    'agent': 'python-cli-architect',
    'dependencies': ['T0'],
    'priority': 1,
    'complexity': 'medium',
    'started': '2026-02-02T15:15:00Z',
    'completed': None,
    'skills': ['fastmcp-python-tests'],
    'issue-classification': 'defect',
    'scenario-target': 'Hook fires late -> fires immediately',
    'analysis-method': '5-whys',
    'divergence-notes': 0,
}
```

**Type conversions:**
- Timestamps parsed as datetime objects by ruamel.yaml → converted back to ISO strings
- Lists preserved as-is (YAML `[T1, T2]` or multiline)
- None values preserved

---

### 2.3 Task Field Resolution (Backward Compatibility)

**Location:** `task_format.py:80-95` (`resolve_task_id()`)

**Pattern:**
```python
def resolve_task_id(fm: dict[str, Any]) -> str | None:
    raw = fm.get("task") if "task" in fm else fm.get("task_id")
    return str(raw) if raw is not None else None
```

**Why:** Older task files use `task:` field; newer ones may use `task_id:`. Parser tries `task` first (preferred), falls back to `task_id`.

**Applied in:** `implementation_manager.py:442` during `parse_task_from_frontmatter()`

---

### 2.4 Single-Task Parsing from Frontmatter

**Location:** `implementation_manager.py:403-471` (`parse_task_from_frontmatter()`)

**Input:** Raw file content with YAML frontmatter

**Validation (lines 436-440):**
```python
missing = [f for f in ("task", "title", "status") if f not in frontmatter]
if missing:
    msg = f"Missing required YAML frontmatter fields: {', '.join(missing)}"
    raise ValueError(msg)
```

**Required fields:** `task`, `title`, `status`
**Optional fields:** Everything else (agent, dependencies, priority, complexity, etc.)

**Status normalization (lines 308-320):**
```python
def _parse_yaml_status(raw_status: str) -> TaskStatus:
    normalized = normalize_status(raw_status)
    if normalized in _YAML_STATUS_TO_ENUM:
        return _YAML_STATUS_TO_ENUM[normalized]
    return TaskStatus.NOT_STARTED
```

**Status normalization (task_format.py:275-320):**
```python
def normalize_status(old_status: str) -> str:
    # Fast path: already normalized (e.g., "in-progress")
    if status_clean in VALID_STATUSES:
        return status_clean
    # Remove Unicode emoji: ✅ → ""
    # Check STATUS_MAP: "NOT STARTED" → "not-started"
    # Default: "not-started"
```

**STATUS_MAP (task_format.py:28-45):**
```python
{
    "NOT STARTED": "not-started",
    "IN PROGRESS": "in-progress",
    "COMPLETE": "complete",
    "BLOCKED": "blocked",
    "DEFERRED": "deferred",
    "SKIPPED": "skipped",
    "WONT FIX": "wont-fix",
    # Emoji variations
    ":x:": "not-started",
    ":white_check_mark:": "complete",
    ":arrows_counterclockwise:": "in-progress",
}
```

**Title-based status override (implementation_manager.py:379-400):**
```python
def _status_from_title(title: str, current_status: TaskStatus) -> TaskStatus:
    if "[DEFERRED]" in title.upper():
        return TaskStatus.DEFERRED
    if "[SKIPPED]" in title.upper():
        return TaskStatus.SKIPPED
    return current_status
```

**Rationale:** Legacy task files used title markers like `[DEFERRED]` but left status as `not-started`. The parser recognizes this pattern.

---

### 2.5 Multi-Task Files (Monolithic Format)

**Location:** `implementation_manager.py:479-544` (`parse_task_content()`)

**Two detection paths:**

**Path 1: Single-task file** — Has `task:` field in frontmatter → Parse as one Task

**Path 2: Multi-task manifest** — Has `feature:` field but NO `task:` field → Manifest followed by embedded per-task blocks in body

**Body parsing (lines 514-544):**
```python
if body:
    segments = re.split(r'\n---+\n', body)
    for segment in segments:
        if not segment.strip():
            continue
        try:
            task = parse_task_from_frontmatter(f"---\n{segment}\n---\n")
            tasks.append(task)
        except (ValueError, TypeError):
            continue
```

**Example multi-task format:**
```yaml
---
feature: validate-plugin
version: "2.0"
description: "Core validation system"
---

## Overview

### Per-task blocks below

---
task: T1
title: Create Data Models
status: not-started
---

### Context

Create ValidationResult...

---
task: T2
title: Port Validators
status: not-started
---

### Context

Port existing validators...
```

---

### 2.6 Directory-Based Task Organization

**Location:** `implementation_manager.py:547-575` (`parse_task_file()`)

**Directory detection (lines 550-561):**
```python
if file_path.is_dir():
    md_files = sorted(file_path.glob("*.md"))
    if not md_files:
        return []
    for md_file in md_files:
        try:
            task = parse_task_from_frontmatter(md_file.read_text(encoding="utf-8"))
            tasks.append(task)
        except ValueError:
            continue
    return tasks
```

**File naming convention:** `{task-id}-{slug}.md`
- Examples: `T1-data-models.md`, `1.1-prepare-host.md`
- Slug: lowercase, hyphens, max 50 chars
- Parser extracts task ID from YAML `task:` field, NOT from filename

**Sorting (implementation_manager.py:543):**
```python
tasks.sort(key=_task_sort_key)
```

**Sort key (lines 617-631):**
```python
def _task_sort_key(task: Task) -> tuple[float, int]:
    """Sort tasks numerically by ID.

    Handles both numeric (1.1) and alphanumeric (T1) IDs.
    Returns (numeric_value, priority).
    """
    parts = task.id.lstrip('T').split('.')
    major = float(parts[0])
    minor = float(parts[1]) if len(parts) > 1 else 0
    numeric_id = major + minor / 100  # 1.1 → 1.01
    return (numeric_id, task.priority.value)
```

---

## 3. Field Extraction and Mapping

### 3.1 YAML Frontmatter Fields to Task Dataclass

**Mapping Table (implementation_manager.py:409-419):**

| YAML Field | Task Attribute | Type | Default | Transformer |
|------------|----------------|------|---------|-------------|
| `task` | `id` | str | — (required) | `str()` |
| `task_id` | `id` | str | — (fallback) | Compat layer |
| `title` | `name` | str | — (required) | `str()` |
| `status` | `status` | TaskStatus | — (required) | `_parse_yaml_status()` |
| `agent` | `agent` | str\|None | None | Strips "none"/"n/a"/"-" |
| `dependencies` | `dependencies` | list[str] | [] | `_parse_yaml_dependencies()` |
| `priority` | `priority` | TaskPriority | TaskPriority.MEDIUM | `TaskPriority(int(...))` |
| `complexity` | `complexity` | str | "medium" | `.capitalize()` |
| `started` | `started` | str\|None | None | `_coerce_timestamp()` |
| `completed` | `completed` | str\|None | None | `_coerce_timestamp()` |
| `skills` | `skills` | list[str] | [] | `_parse_yaml_skills()` |

### 3.2 Optional Analytical Fields (Not Used by Parser)

These fields are defined in TASK_FILE_FORMAT.md but **NOT extracted by parsers** (agents may use them):

- `issue-classification` — enum: procedural, defect, recurring-pattern, missing-guardrail, unbounded-design
- `scenario-target` — string: "{scenario} -> {improvement}"
- `analysis-method` — enum: none, 5-whys, 6-sigma, design-framing
- `divergence-notes` — integer count
- `blocked-by` — list of external blockers
- `parallelize-with` — list of task IDs that can run concurrently
- `created` — timestamp

**Implication:** These fields round-trip through YAML but are NOT used by `implementation_manager.py` or task scheduling logic. They're metadata for agents.

---

### 3.3 Dependencies Parsing

**Location:** `implementation_manager.py:273-300` (`parse_dependencies()`)

**Input formats supported:**
```python
"Task 1, Task 2"        # legacy numeric
"Task 1.1, Task 1.2"    # legacy dotted
"Task T1, Task T2"      # with prefix
"T1, T2"                # bare IDs
"None"                  # no dependencies
"T1, 1.1, T2.3"         # mixed numeric and alphanumeric
```

**Patterns (lines 293-300):**
```python
# Try "Task X" pattern first (legacy format)
task_pattern = r"Task\s+([A-Za-z0-9]+(?:\.\d+)?)"
matches = re.findall(task_pattern, dep_text, re.IGNORECASE)
if matches:
    return matches

# Fall back to bare alphanumeric IDs
bare_pattern = r"\b([A-Z]?\d+(?:\.\d+)?)\b"
return re.findall(bare_pattern, dep_text)
```

**YAML dependencies array (implementation_manager.py:340-357):**
```python
def _parse_yaml_dependencies(raw_deps: list[str] | str | None) -> list[str]:
    if raw_deps is None:
        return []
    if isinstance(raw_deps, list):
        return [str(dep) for dep in raw_deps]
    if isinstance(raw_deps, str):
        return parse_dependencies(raw_deps)
    return []
```

---

### 3.4 Skills Parsing

**Location:** `implementation_manager.py:360-376` (`_parse_yaml_skills()`)

**Input formats:**
```yaml
skills: [skill1, skill2]              # YAML list
skills: "skill1, skill2"              # Comma-separated string
skills: []                            # Empty list
```

**Parsing:**
```python
def _parse_yaml_skills(raw_skills: list[str] | str | None) -> list[str]:
    if isinstance(raw_skills, list):
        return [str(s) for s in raw_skills if s]
    if isinstance(raw_skills, str) and raw_skills:
        return [s.strip() for s in raw_skills.split(",") if s.strip()]
    return []
```

---

## 4. Status Update Patterns

### 4.1 Lifecycle Status Values

**Defined in:** `task_format.py:49-57` (VALID_STATUSES)

**Valid statuses:**
```python
"not-started"
"in-progress"
"complete"
"blocked"
"deferred"      # terminal status
"skipped"       # terminal status
"wont-fix"      # alias for skipped
```

**Terminal statuses (implementation_manager.py:100):**
```python
_TERMINAL_STATUSES: frozenset[TaskStatus] = frozenset({
    TaskStatus.COMPLETE,
    TaskStatus.DEFERRED,
    TaskStatus.SKIPPED
})
```

**Used in:** `get_ready_tasks()` to determine if a task with dependencies is unblocked.

---

### 4.2 Status Update Mechanism (Hook Integration)

**Hook script:** `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py`

**Events handled:**

1. **SubagentStop** — Task execution completes
   - Parse prompt for `/start-task {path} --task {id}`
   - Read task file
   - Update `status: in-progress` → `status: complete`
   - Add `completed: {ISO timestamp}`
   - Delete context file `.claude/context/active-task-{session_id}.json`
   - Attempt GitHub sync (best-effort, non-fatal failure)

2. **PostToolUse (Write|Edit|Bash)** — Activity during task execution
   - Read context file to find active task
   - Update `last_activity: {ISO timestamp}`
   - Guard: Skip if task status is already `complete`

**Field update (task_format.py:179-241):**
```python
def update_yaml_field(content: str, field: str, value: str | int | list[str]) -> str:
    """Update a single field in YAML frontmatter without re-serializing."""
    # Parse frontmatter boundaries
    # Find existing field line (regex search)
    # Replace line in-place OR insert before closing ---
    # Return updated content
```

**Why regex-based update?** Preserves:
- YAML field order
- Comments and formatting
- Body content exactly as-is

---

### 4.3 Timestamp Coercion

**Location:** `implementation_manager.py:323-337` (`_coerce_timestamp()`)

**Problem:** ruamel.yaml parses ISO 8601 timestamps as datetime objects

**Solution:**
```python
def _coerce_timestamp(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    return str(value)  # datetime.__str__() produces ISO format
```

**Result:** Timestamps remain ISO 8601 strings throughout Task object lifecycle.

---

## 5. Task ID Resolution and Validation

### 5.1 Task ID Pattern

**Defined in:** `task_format.py:47`

```python
TASK_ID_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z]?\d+(\.\d+)?$")
```

**Valid examples:**
- `1`, `1.1`, `1.2.3` (numeric)
- `T1`, `T2`, `T10` (alphanumeric with prefix)
- `P1`, `S1`, `A3` (any letter prefix)

**Invalid examples:**
- `Task-1` (contains hyphen)
- `1T` (letter suffix, not prefix)
- `task1` (lowercase letter prefix)

---

### 5.2 P/T Addressing Scheme Mapping

**Observation:** The codebase currently has **no P/T addressing scheme**. Task IDs are simple numeric or alphanumeric (T1, 1.1, etc.).

**What's missing:** No code maps P (parent issue) or T (task ID within feature) to file paths or structured addresses.

**If P/T scheme were adopted:**
- P = parent story GitHub issue number (e.g., P714 = issue #714)
- T = task number within the story (e.g., T3 = task 3 in the story)
- Full address: P714-T3 or similar

**Integration point:** `task_status_hook.py` already tracks `parent_issue_number` in context file (line 72, 90). This is the infrastructure to support it.

---

## 6. Dependency Resolution and Readiness Logic

### 6.1 Ready Task Identification

**Location:** `implementation_manager.py:799-819` (`get_ready_tasks()`)

**Definition: "Ready" means:**
1. Status is `NOT_STARTED`
2. All dependencies have status in `_TERMINAL_STATUSES`

**Code:**
```python
def get_ready_tasks(tasks: list[Task]) -> list[Task]:
    ready = []
    for task in tasks:
        if task.status != TaskStatus.NOT_STARTED:
            continue

        # Check if all dependencies are terminal
        if not task.dependencies:
            ready.append(task)
        else:
            all_deps_done = all(
                any(t.id == dep and t.status in _TERMINAL_STATUSES
                    for t in tasks)
                for dep in task.dependencies
            )
            if all_deps_done:
                ready.append(task)

    return ready
```

---

### 6.2 Dependency Graph Limitations

**What the parser does NOT do:**
- Cycle detection
- Transitive dependency resolution
- Partial completion (blocking only on direct deps, not transitive)
- Dependency graph visualization

**Risk:** Circular dependencies will create deadlock — parser returns empty ready list and stops.

---

## 7. Test Infrastructure

### 7.1 Unit Tests

**Location:** `plugins/python3-development/skills/implementation-manager/tests/`

**Test coverage:**

| File | Focus | Coverage |
|------|-------|----------|
| `test_task_parsing.py` | Bare YAML frontmatter, status parsing, DEFERRED/SKIPPED | parse_task_content, parse_status, title-override |
| `test_task_status_hook/test_subagent_stop_integration.py` | Full SubagentStop path with GitHub sync | handle_subagent_stop, context file cleanup |
| `test_task_status_hook/test_github_sync.py` | GitHub sync failures (if present) | (not examined in detail) |

**Test standards (test_task_parsing.py:1-17):**
- AAA pattern (Arrange-Act-Assert)
- Full type annotations
- monkeypatch for stderr (no unittest.mock)
- No shared mutable state
- Isolated fixtures

---

### 7.2 Test Task Fixtures

**Minimal task (test_task_parsing.py:40-50):**
```python
_MINIMAL_TASK_YAML = (
    "---\n"
    "task: T1\n"
    "title: Minimal Task\n"
    "status: not-started\n"
    "agent: general-purpose\n"
    "dependencies: []\n"
    "priority: 1\n"
    "complexity: low\n"
    "---\n"
)
```

**Deferred task (lines 52-62):**
```python
_DEFERRED_TASK_YAML = (
    "---\n"
    "task: T3\n"
    "title: Deferred Task\n"
    "status: deferred\n"
    ...
)
```

**Title-based deferred (lines 76-86):**
```python
_DEFERRED_TITLE_YAML = (
    "---\n"
    "task: T5\n"
    "title: '[DEFERRED] Intentionally deferred task'\n"
    "status: not-started\n"  # Parser overrides to DEFERRED
    ...
)
```

---

## 8. MCP Server Integration Points

### 8.1 Current State

**MCP Server:** `.claude/skills/backlog/backlog_core/server.py`

**Exposed tools:**
- `backlog_add`, `backlog_list`, `backlog_view`, `backlog_update`, `backlog_sync`, `backlog_close`, etc.

**SAM task integration:** NOT YET IMPLEMENTED

**Future tool (from local-workflow.md):** `backlog_get_ready_sam_tasks(parent_issue_number=N)`

**Expected output shape:**
```json
{
  "feature": "feature-name",
  "ready_tasks": [
    {
      "id": "T1",
      "name": "Task 1",
      "status": "NOT STARTED",
      "skills": ["skill1", "skill2"]
    }
  ],
  "count": 1
}
```

---

### 8.2 Integration Blockers

**What MCP server needs:**
1. Access to task file discovery logic (currently in `implementation_manager.py`)
2. Access to task parsing logic
3. Ability to query GitHub for parent issue number
4. Ability to map issue number → task file path

**Current workaround:** Implementation uses CLI fallback:
```bash
uv run ./plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py \
  ready-tasks . "{slug}" --github --parent-issue N
```

**Missing from MCP:** Native Python method to get ready tasks without spawning subprocess.

---

## 9. Pyproject.toml Dependencies

**YAML library:** `ruamel.yaml>=0.18.0`

**Why ruamel.yaml?** Preserves YAML formatting, comments, field order. `pyyaml` loses these during round-trip.

**Type validation:** NOT using pydantic for Task dataclass (uses stdlib `dataclass`)

**JSON validation:** NOT using jsonschema (schema defined in TASK_FILE_FORMAT.md but unenforced)

**Recommended enhancement:** Add pydantic for runtime schema validation:
```toml
pydantic>=2.12.3
```

(Already in pyproject.toml for other uses)

---

## 10. Identified Gaps Between Specification and Implementation

### 10.1 Spec-Defined Fields NOT Extracted by Parser

**File:** `.claude/docs/TASK_FILE_FORMAT.md` lines 150-154

**Fields defined but not used:**
- `issue-classification` (enum: procedural, defect, etc.)
- `scenario-target` (string)
- `analysis-method` (enum: none, 5-whys, etc.)
- `divergence-notes` (integer)
- `blocked-by` (array)
- `parallelize-with` (array)
- `created` (datetime)

**Impact:** These round-trip through YAML but are never loaded into Task dataclass. Agents can edit them, but orchestrator cannot query them.

**Risk:** Orchestrator cannot enforce `parallelize-with` constraints or route tasks by `issue-classification`.

---

### 10.2 Task Dataclass Missing Fields

**File:** `implementation_manager.py:117-143` (Task dataclass)

**Dataclass fields:**
```python
id, name, status, dependencies, agent, priority, complexity, started, completed, skills
```

**Missing:**
- `created` timestamp
- `blocked_by` external blockers
- `parallelize_with` task IDs
- `issue_classification` enum
- `scenario_target` string
- `analysis_method` enum
- `divergence_notes` count

**Consequence:** Agents cannot query task creation date, parallelization hints, or analysis metadata via the Python API. They must read YAML directly.

---

### 10.3 Schema Validation NOT Enforced

**Spec:** TASK_FILE_FORMAT.md line 366-481 defines JSON schema for all fields

**Implementation:** No jsonschema validation in parsers

**Current validation:** Only required field check (task, title, status):
```python
missing = [f for f in ("task", "title", "status") if f not in frontmatter]
if missing:
    raise ValueError(...)
```

**Missing validation:**
- Task ID pattern `^[A-Z]?\d+(\.\d+)?$`
- Priority range 1-5
- Complexity enum: low/medium/high
- Status enum: not-started/in-progress/complete/blocked/deferred/skipped
- Timestamp format ISO 8601

**Risk:** Malformed YAML (e.g., `priority: 10` or `status: "started"`) silently degrades to defaults instead of failing loudly.

---

### 10.4 Multi-YAML-Fence Edge Case

**Problem (observed in real task files):** Task files with multiple YAML blocks within the body

**Example:**
```markdown
---
task: T1
title: Main Task
status: complete
---

## Objective

```yaml
---
nested_config:
  value: 123
---
```

This is valid markdown (YAML code fence) but **breaks multi-task parsing** in `parse_task_content()` at line 514:
```python
segments = re.split(r'\n---+\n', body)
```

The regex treats the inner `---` as a segment delimiter, creating a malformed segment that fails parsing.

**File affected:** `plan/tasks-1-backlog-state-reconciliation.md` (lines 1-19 show minimal header but body may have code fences)

---

## 11. Parser Error Handling

### 11.1 Graceful Degradation

**YAML parse failure (task_format.py:161-165):**
```python
try:
    parsed = _yaml.load(raw_yaml)
except YAMLError as exc:
    msg = f"YAML parsing failed: {exc}"
    raise ValueError(msg) from exc
```

**Error propagates.** Caller may catch and skip the task:
```python
try:
    task = parse_task_from_frontmatter(content)
    tasks.append(task)
except (ValueError, TypeError):
    continue  # skip unparseable task
```

**Implication:** Malformed tasks are silently skipped. Orchestrator sees them as missing, not as an error.

---

### 11.2 Missing Required Field Handling

**Location:** `implementation_manager.py:436-440`

```python
missing = [f for f in ("task", "title", "status") if f not in frontmatter]
if missing:
    msg = f"Missing required YAML frontmatter fields: {', '.join(missing)}"
    raise ValueError(msg)
```

**Behavior:**
- Raises `ValueError` with specific missing fields
- Caller catches and skips the task
- No logging or stderr output (silent failure)

**Risk:** Missing required field creates a "ghost task" — defined in file but never visible to orchestrator.

---

## 12. Patterns for Adding New Fields

### 12.1 To Support a New Optional Field

**Steps:**

1. **Add to TASK_FILE_FORMAT.md** (spec file)
   - Add to Optional Fields table (line 138-154)
   - Add to JSON schema properties (line 370-480)
   - Document validation rules if applicable

2. **Add to Task dataclass** (`implementation_manager.py:117-143`)
   ```python
   @dataclass
   class Task:
       id: str
       name: str
       status: TaskStatus
       # ... existing fields ...
       new_field: NewType | None = None  # Add here
   ```

3. **Add extraction logic** (`implementation_manager.py:403-471`)
   ```python
   def parse_task_from_frontmatter(content: str) -> Task:
       # ... after parsing dependencies ...
       new_field = frontmatter.get("new_field")
       if new_field is not None:
           new_field = coerce_new_field(new_field)  # Add transformer if needed
   ```

4. **Add to Task.to_dict()** (`implementation_manager.py:145-162`)
   ```python
   def to_dict(self) -> TaskDict:
       return TaskDict(
           # ... existing fields ...
           new_field=self.new_field,
       )
   ```

5. **Update TaskDict TypedDict** (`implementation_manager.py:207-223`)
   ```python
   class TaskDict(TypedDict):
       new_field: NewType | None
   ```

6. **Add test fixture** (`test_task_parsing.py`)
   ```python
   _TASK_WITH_NEW_FIELD = (
       "---\n"
       "task: T1\n"
       # ... existing fields ...
       "new_field: value\n"
       "---\n"
   )
   ```

7. **Add parsing test**
   ```python
   def test_parse_task_with_new_field():
       task = im.parse_task_from_frontmatter(_TASK_WITH_NEW_FIELD)
       assert task.new_field == expected_value
   ```

---

### 12.2 To Enforce a Field's Value Range

**Pattern:** Use enum for status, priority, complexity values

**Example (priority validation):**
```python
class TaskPriority(IntEnum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    LOWEST = 5

# In parser:
raw_priority = frontmatter.get("priority")
priority = TaskPriority(int(raw_priority)) if raw_priority is not None else TaskPriority.MEDIUM
# Raises ValueError if out of range
```

**Pattern for string enums:**
```python
VALID_COMPLEXITIES: frozenset[str] = frozenset({"low", "medium", "high"})

# Validation
if complexity not in VALID_COMPLEXITIES:
    raise ValueError(f"Invalid complexity: {complexity}")
```

---

## 13. Recommendations for Parser Enhancement

### 13.1 Add JSON Schema Validation

**Where:** `task_format.py` — add new function

```python
from jsonschema import validate, ValidationError

TASK_SCHEMA = {
    "type": "object",
    "required": ["task", "title", "status"],
    "properties": {
        "task": {"type": "string", "pattern": "^[A-Za-z]?\\d+(\\.\\d+)?$"},
        "title": {"type": "string", "minLength": 5, "maxLength": 100},
        "status": {
            "type": "string",
            "enum": ["not-started", "in-progress", "complete", "blocked", "deferred", "skipped"]
        },
        "priority": {"type": "integer", "minimum": 1, "maximum": 5},
        "complexity": {"type": "string", "enum": ["low", "medium", "high"]},
        # ... rest of schema ...
    }
}

def validate_task_frontmatter(frontmatter: dict) -> None:
    """Validate frontmatter against JSON schema."""
    try:
        validate(instance=frontmatter, schema=TASK_SCHEMA)
    except ValidationError as e:
        raise ValueError(f"Task validation error: {e.message}") from e
```

**Call in:** `parse_task_from_frontmatter()` after extracting required fields

---

### 13.2 Detect and Fix Multi-YAML-Fence Issue

**Where:** `parse_task_content()` — enhance body parsing

```python
def _sanitize_body_for_segment_split(body: str) -> str:
    """Escape YAML fences in body to prevent false delimiters during split.

    Temporary workaround until proper multi-stage parsing is implemented.
    """
    # Find all code fences in body
    lines = body.split('\n')
    result = []
    in_code_fence = False

    for line in lines:
        if line.startswith('```') or line.startswith('~~~'):
            in_code_fence = not in_code_fence
            result.append(line)
        elif in_code_fence and line.strip() == '---':
            # Escape internal --- in code fences
            result.append('\\---')
        else:
            result.append(line)

    return '\n'.join(result)
```

---

### 13.3 Add Spec-Defined Fields to Task Dataclass

**Migration:** Update Task to include all optional fields from TASK_FILE_FORMAT.md

```python
@dataclass
class Task:
    id: str
    name: str
    status: TaskStatus
    dependencies: list[str] = field(default_factory=list)
    agent: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    complexity: str = "medium"
    started: str | None = None
    completed: str | None = None
    skills: list[str] = field(default_factory=list)
    # NEW FIELDS:
    created: str | None = None
    blocked_by: list[str] = field(default_factory=list)
    parallelize_with: list[str] = field(default_factory=list)
    issue_classification: str | None = None  # enum: procedural, defect, etc.
    scenario_target: str | None = None
    analysis_method: str | None = None  # enum: none, 5-whys, 6-sigma, design-framing
    divergence_notes: int = 0
```

**Benefit:** Orchestrator can now query task metadata for parallelization, analysis history, etc.

---

## 14. Integration with MCP Server

### 14.1 Proposed `backlog_get_ready_sam_tasks()` Implementation

**Location:** `.claude/skills/backlog/backlog_core/server.py`

```python
@mcp.tool()
async def backlog_get_ready_sam_tasks(
    parent_issue_number: Annotated[int, Field(description="GitHub issue number of the parent story")]
) -> dict:
    """Get ready tasks from a SAM task file linked to a GitHub issue.

    Returns:
        Dict with feature name, ready tasks list, and count.
    """
    # 1. Load issue from GitHub (using backlog_core.github module)
    # 2. Extract plan artifact reference from issue body
    # 3. Find task file by slug
    # 4. Parse task file
    # 5. Call get_ready_tasks()
    # 6. Return JSON-serialized Task objects with skills
```

---

### 14.2 CLI Fallback (Current Implementation)

**Location:** `implementation_manager.py` CLI commands

**Command:** `ready-tasks`
```bash
implementation_manager.py ready-tasks /path/to/project feature-slug
```

**Output:**
```json
{
  "ready_tasks": [
    {
      "id": "T1",
      "name": "Task 1",
      "status": "NOT STARTED",
      "dependencies": ["T0"],
      "agent": "python-cli-architect",
      "priority": 1,
      "complexity": "Low",
      "started": null,
      "completed": null,
      "skills": ["fastmcp-python-tests", "python3-development"]
    }
  ],
  "count": 1
}
```

---

## Summary: Key Takeaways for Downstream Agents

### For Implementers

1. **Task files use YAML frontmatter** (not markdown regex) — start with `---\n`
2. **Required fields:** `task`, `title`, `status` — all others optional
3. **Use ruamel.yaml** for parsing/writing, never pyyaml
4. **Status values:** "not-started", "in-progress", "complete", "blocked", "deferred", "skipped"
5. **Task IDs:** Pattern `^[A-Za-z]?\d+(\.\d+)?$` — numeric or alphanumeric with prefix
6. **Timestamps:** ISO 8601 with timezone (2026-02-02T15:00:00Z)
7. **Skills field:** List of skill names the sub-agent should load
8. **Priorities:** Integer 1-5 (1=highest)
9. **Complexity:** "low", "medium", "high"

### For Test Writers

1. Use fixtures with raw YAML strings, not code fences
2. Test status normalization separately (regex pattern matching in `parse_status()`)
3. Test directory vs. file discovery (both paths in `parse_task_file()`)
4. Test timestamp coercion (datetime → ISO string)
5. Test dependency resolution (ready task logic)
6. Test field updates in-place (regex-based, preserves order)

### For Architecture

1. **Three parsers exist but should consolidate:**
   - `parse_task_from_frontmatter()` — single-task YAML
   - `parse_task_content()` — multi-task manifest
   - Legacy markdown (deprecated, no new code uses it)

2. **Missing pieces:**
   - JSON schema validation (currently manual checks only)
   - P/T addressing scheme (infrastructure exists, not implemented)
   - Multi-YAML-fence handling (current regex breaks on code fences)
   - Spec-defined fields in Task dataclass (round-trip but not accessible)

3. **Integration points:**
   - Hook script reads `.claude/context/active-task-{session_id}.json` for context
   - Hook calls `update_yaml_field()` for atomic field updates
   - MCP server needs `backlog_get_ready_sam_tasks()` for non-CLI queries

