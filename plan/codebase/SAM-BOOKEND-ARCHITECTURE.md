# SAM Bookend Validation Architecture

**Analysis Date:** 2026-03-15
**Focus:** T0 (baseline capture) and TN (verification gate) bookend task support in SAM plans
**Scope:** sam_schema package + SAM execution workflow

---

## Current SAM Architecture

### 1. sam_schema Package Structure

**Location:** `packages/sam_schema/sam_schema/`

Core layers:

- **`core/models.py`** — Canonical data models (Task, Plan, TaskStatus, enums)
- **`core/query.py`** — Query and update API (load_plan, get_ready_tasks, update_status)
- **`core/dependencies.py`** — Dependency graph & readiness logic
- **`readers/`** — Format detection and parsing (YAML, markdown frontmatter, legacy)
- **`writers/yaml_writer.py`** — Atomic YAML field updates
- **`server.py`** — MCP server exposing task/plan queries

### 2. Task Model

**File:** `packages/sam_schema/sam_schema/core/models.py:92-173`

Key fields relevant to bookends:

```python
class Task(BaseModel):
    id: str                        # Task ID: "T0", "T1", "TN", etc.
    title: str
    status: TaskStatus             # not-started, in-progress, complete, blocked, deferred, skipped
    dependencies: list[str]        # Task IDs this task depends on
    priority: Priority             # IntEnum 1-5 (lower=higher priority)
    complexity: Complexity         # low, medium, high

    # Content fields (YAML multiline scalars)
    objective: str                 # One-sentence definition of done
    acceptance_criteria: str       # Specific, measurable requirements
    verification_steps: str        # How to verify task complete
    expected_outputs: str          # Files/artifacts produced

    started: datetime | None       # Set by /start-task skill
    completed: datetime | None     # Set by task_status_hook.py
    last_activity: datetime | None # Updated by PostToolUse hook
```

### 3. Plan Model

**File:** `packages/sam_schema/sam_schema/core/models.py:175-224`

```python
class Plan(BaseModel):
    feature: str                   # Feature slug identifier
    version: str                   # Plan version (default: "1.0")
    goal: str | None               # Feature goal statement
    acceptance_criteria: str | None # Plan-level acceptance criteria
    tasks: list[Task]              # All tasks in plan
```

### 4. Readiness and Execution

**File:** `packages/sam_schema/sam_schema/core/query.py:82-100`

Task readiness logic:

```python
def get_ready_tasks(plan_path: Path) -> list[Task]:
    """Task is ready when:
    1. status == 'not-started'
    2. all tasks in dependencies[] have terminal status (complete, deferred, skipped)
    """
    result = load_plan(plan_path)
    graph = DependencyGraph(result.plan.tasks)
    return graph.get_ready_tasks()
```

Implemented via `DependencyGraph` which:
- Validates for cycles
- Returns ready tasks sorted by priority then ID
- Identifies blocked tasks and missing dependencies

### 5. Task Execution Flow

**Phase 1: Dispatching** (`/implement-feature` skill)

```
Query status/ready-tasks
  ↓
For each ready task:
  - Route to task's agent
  - Load task skills
  - Invoke /start-task skill
  ↓
Hook auto-updates task status/timestamps
  ↓
Repeat until no tasks remain ready
```

**Phase 2a: Hook Updates** (`task_status_hook.py`)

| Hook Event | Action |
|-----------|--------|
| `SubagentStop` | Set status=complete, add Completed timestamp |
| `PostToolUse` | Update LastActivity timestamp |

**Phase 3: Quality Gates** (`/complete-implementation` skill)

```
Code Review (may create follow-ups)
  ↓
Feature Verification (checks plan & task acceptance criteria)
  ↓
Integration Check
  ↓
Doc Audit/Update
  ↓
Context Refinement
```

### 6. Acceptance Criteria Usage

**Task-level:** `Task.acceptance_criteria` field

- Stored as YAML multiline scalar
- Read by agents during `/start-task` execution
- Verified by `feature-verifier` agent in complete-implementation Phase 2

**Plan-level:** `Plan.acceptance_criteria` field

- Represents acceptance criteria for entire feature
- Used by `feature-verifier` for goal-backward verification

---

## Bookend Task Requirements

### T0 (Baseline Capture) — Runs FIRST

**Purpose:** Capture baseline metrics/state before implementation begins

**Constraints:**
- Must have `dependencies: []` (no dependencies → ready immediately)
- Must run before all other implementation tasks
- Must complete before TN can begin

**Current Support:**
- ✓ Task model supports baseline task creation
- ✓ Readiness logic naturally handles root tasks
- ✓ Priority field allows forcing first execution

**Gap:** No explicit marking; relies on ID naming convention ("T0") or priority tweaking

### TN (Verification Gate) — Runs LAST

**Purpose:** Verify goal achievement against baseline and implementation

**Constraints:**
- Must depend on ALL implementation tasks: `dependencies: ["T1", "T2", "T3", ...]`
- Must run after all implementation complete
- Must compare against T0 baseline

**Current Support:**
- ✓ Task model supports verification task creation
- ✓ Readiness logic honors dependencies
- ✓ Acceptance criteria can reference T0 findings

**Gap:** No explicit marking; no automated dependency generation

---

## Integration Points for Bookends

### 1. swarm-task-planner Agent

**File:** `plugins/python3-development/agents/swarm-task-planner.md`

**Current:** Creates task decomposition from architecture spec

**For bookends:**
- T0 task must be created first, with `dependencies: []`
- TN task must be created last, with `dependencies: [all_implementation_task_ids]`
- Both need acceptance_criteria that reference baseline/goal comparison

**Implementation approach:**
- Add to agent prompt: rules for bookend task generation
- T0 should have objective like "Capture baseline state before implementation"
- TN should have objective like "Verify goal achievement vs baseline"

### 2. feature-verifier Agent

**File:** `plugins/python3-development/agents/feature-verifier.md` (not fully analyzed)

**For bookends:**
- Reads Plan.acceptance_criteria and Task.acceptance_criteria
- Compares TN findings against T0 baseline
- Verifies feature goal achievement

### 3. code-reviewer Agent

**File:** `plugins/python3-development/agents/code-reviewer.md` (not fully analyzed)

**For bookends:**
- May create follow-ups that reference T0 baseline
- Should be aware T0 captures pre-implementation state

### 4. Task Status Tracking

**Files:**
- `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py`
- `packages/sam_schema/sam_schema/writers/yaml_writer.py`

**Current:** Tracks `started`, `completed`, `last_activity` timestamps

**For bookends:**
- T0 completion time marks "baseline capture complete"
- TN start time marks "verification begins"
- Timing enables delta analysis (TN - T0 = implementation duration)

---

## Three Implementation Approaches for Bookends

### Option A: Explicit Model Fields (Strongest)

**File to modify:** `packages/sam_schema/sam_schema/core/models.py`

Add to Task model:

```python
class Task(BaseModel):
    ...
    is_t0_baseline: bool = False           # NEW
    is_tn_verification: bool = False       # NEW
    ...
```

Add to Plan model:

```python
class Plan(BaseModel):
    ...
    t0_baseline_task_id: str | None = None     # NEW
    tn_verification_task_id: str | None = None  # NEW
    ...
```

**Impact:**
- Schema version bump required
- Reader/writer updates needed for all formats
- Test fixtures updated
- Clear semantic meaning in code

**Advantages:**
- Type-safe; explicit in schema
- Easy to query/validate
- Self-documenting

**Disadvantages:**
- Schema evolution required
- Format readers must handle backward compatibility

### Option B: Convention-Based (Minimal Change)

Mark bookends via existing fields:

- **Task ID:** Use `"T0"` and `"TN"` as reserved IDs
- **Title prefix:** `"T0: ..."` for baseline, `"TN: ..."` for verification
- **Priority:** Set `priority=Priority.CRITICAL` (1) for both
- **Objective:** Include "baseline" or "verification" keywords

**Impact:**
- Zero schema changes
- No reader/writer updates
- Works immediately with all format readers

**Advantages:**
- Backward compatible
- No schema versioning needed
- Simple to implement

**Disadvantages:**
- Convention-based; not enforced
- Requires agent discipline (swarm-task-planner must follow convention)
- Less discoverable in code

### Option C: Hybrid (Recommended)

Combine Option A (model fields) with validation in `core/dependencies.py`:

1. Add optional boolean fields to Task/Plan models
2. Make fields default to `False` (backward compatible)
3. Add validation logic in DependencyGraph:
   - Ensure T0 (if marked) has no dependencies
   - Ensure TN (if marked) depends on all non-bookend tasks
   - Ensure only one T0 and one TN per plan
4. Readers parse both explicit fields and ID convention
5. Normalizer auto-detects bookends if not explicitly marked

```python
# In DependencyGraph or new BookendValidator class
def validate_bookend_structure(plan: Plan) -> list[str]:
    """Returns validation errors if any."""
    t0_tasks = [t for t in plan.tasks if t.is_t0_baseline or t.id == "T0"]
    tn_tasks = [t for t in plan.tasks if t.is_tn_verification or t.id == "TN"]

    errors = []
    if len(t0_tasks) > 1:
        errors.append("Only one T0 baseline task allowed")
    if len(tn_tasks) > 1:
        errors.append("Only one TN verification task allowed")

    if t0_tasks and t0_tasks[0].dependencies:
        errors.append("T0 baseline must have no dependencies")

    if tn_tasks and not tn_tasks[0].dependencies:
        errors.append("TN verification must depend on implementation tasks")

    return errors
```

---

## Data Flow for Bookend Tasks

### T0 (Baseline) Capture

```
/add-new-feature (planning phase)
  ↓
swarm-task-planner creates T0 task:
  id: "T0"
  title: "T0: Capture baseline state"
  dependencies: []
  status: not-started
  objective: "Capture pre-implementation baseline metrics"
  expected_outputs: "baseline-snapshot.json, baseline-results.txt"

  ↓
/implement-feature (execution phase)
  ↓
T0 becomes ready immediately (no dependencies)
  ↓
Task routed to capturing agent (e.g., metrics-collector)
  ↓
/start-task executes T0:
  - Agent runs baseline capture
  - Writes baseline-snapshot.json
  - Verification steps confirm snapshot created

  ↓
task_status_hook.py (SubagentStop):
  - Sets T0 status = "complete"
  - Records completed timestamp (T0_time)

  ↓
All other implementation tasks (T1...TN-1):
  - Each depends on T0
  - Each depends on previous tasks
  - Execute in dependency order
```

### TN (Verification) Gate

```
After all implementation tasks complete (T1...TN-1 = complete):
  ↓
TN becomes ready (all dependencies met)
  ↓
Task routed to verification agent (feature-verifier)
  ↓
/start-task executes TN:
  - Agent reads T0 baseline snapshot
  - Agent reads Plan.goal and Plan.acceptance_criteria
  - Agent runs verification checks
  - Agent compares results to T0 baseline
  - Verification steps check delta against baseline
  - Writes verification-report.json

  ↓
task_status_hook.py (SubagentStop):
  - Sets TN status = "complete"
  - Records completed timestamp (TN_time)

  ↓
Implementation duration = TN_time - T0_time
  ↓
/complete-implementation Phase 2 (feature-verifier):
  - Reads TN results
  - Compares against Plan.goal
  - Confirms feature achieved goal
```

---

## Affected Modules and Update Scope

### Must Update

1. **`packages/sam_schema/sam_schema/core/models.py`**
   - Add optional bookend fields to Task and Plan
   - Add docstrings explaining T0/TN semantics

2. **`packages/sam_schema/sam_schema/core/dependencies.py`**
   - Add bookend validation logic
   - Update DependencyGraph to handle T0 and TN constraints

3. **`plugins/python3-development/agents/swarm-task-planner.md`**
   - Update agent prompt to generate T0 and TN tasks
   - Define T0/TN conventions (ID, title, dependencies)
   - Add rules for T0 baseline task creation
   - Add rules for TN task creation with correct dependencies

### Should Update (Consistency)

4. **`packages/sam_schema/sam_schema/readers/`** (all format readers)
   - Parse bookend fields from YAML/markdown
   - Handle both explicit fields and ID convention detection

5. **`packages/sam_schema/sam_schema/writers/yaml_writer.py`**
   - Ensure bookend fields roundtrip correctly in updates

### May Update (Enhancement)

6. **`plugins/python3-development/agents/feature-verifier.md`**
   - Add logic to read T0 baseline snapshot
   - Enhance verification to check delta vs baseline

7. **`plugins/python3-development/agents/code-reviewer.md`**
   - Awareness that T0 exists as baseline reference
   - May create follow-ups that reference baseline

### No Changes Needed

- `plugins/python3-development/skills/implement-feature/SKILL.md` — generic execution loop
- `plugins/python3-development/skills/complete-implementation/SKILL.md` — phases apply as-is
- `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` — timestamps auto-captured
- `packages/sam_schema/sam_schema/core/query.py` — readiness logic unchanged

---

## Recommended Approach

**Use Option C (Hybrid):**

1. Add optional boolean fields to Task/Plan models (backward compatible)
2. Add validation rules in dependencies.py
3. Update swarm-task-planner to generate T0/TN with correct structure
4. Use ID convention as fallback (for plans created without explicit fields)
5. Implement bookend validation in plan-validator agent (Phase 5 of /add-new-feature)

**Rationale:**
- Minimal schema evolution (fields optional)
- Backward compatible with existing plans
- Self-enforcing via validation
- Clear semantics in code
- Agent discipline reinforced by validation

---

*Analysis completed: 2026-03-15*
