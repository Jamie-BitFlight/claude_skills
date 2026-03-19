# Utilization Proposals: SimpleMem-Cross

**Research entry**: ./research/context-management/simplemem-cross.md
**Generated**: 2026-03-19
**Integration surfaces found**: 3 (Python async library, HTTP REST API, MCP tools)
**Proposals written**: 3
**Skipped**: 1 — agent-orchestration skill scope does not overlap with memory lifecycle hooks

---

## Utilization 1: context-gathering agent → SimpleMem-Cross cross-session memory

**Research entry**: ./research/context-management/simplemem-cross.md
**Caller**: ./plugins/python3-development/agents/context-gathering.md
**Integration mechanism**: Python async library (pip dependency `simplemem[cross]`)
**Replaces or adds**: Adds persistent cross-session context discovery — agents currently re-discover context from scratch each session
**Setup cost**: Medium (async integration with sam CLI, context manifest serialization layer)
**Integration surface**: `cross.orchestrator.create_orchestrator()`, `await orch.start_session()`, `await orch.stop_session()`

### Why this caller

The context-gathering agent reads task files and performs expensive codebase research to assemble complete context manifests for implementation agents. Currently, every new task triggers a full re-scan of the codebase even when discovering similar context (e.g., "find all CLI command patterns"). SimpleMem-Cross would record discoveries (file paths, patterns, architectural insights) from completed tasks and auto-inject relevant prior findings at the start of the next task via `start_session()`. This reduces redundant research, accelerates context manifest assembly, and maintains a persistent record of what architectural patterns have been discovered across the project.

**Current gap**: context-gathering reads files, identifies patterns, writes narrative descriptions. If tasks involve similar domains (e.g., two tasks both requiring CLI architecture understanding), there is no mechanism to retrieve prior discoveries. SimpleMem-Cross' token-budgeted context injection (`max_context_tokens=2000` by default) would allow the agent to begin each new task with semantically-ranked relevant findings from prior sessions.

### Integration sketch

```python
# Pseudocode: context-gathering agent main flow

from cross.orchestrator import create_orchestrator
import asyncio

async def gather_context(task_file_path):
    # Initialize SimpleMem-Cross orchestrator (once per feature)
    orch = create_orchestrator(project="claude-skills", tenant_id="context-gathering")

    # Read task file metadata
    task_info = read_task_file(task_file_path)  # existing logic

    # Start session: auto-inject relevant prior findings
    result = await orch.start_session(
        content_session_id=task_info["task_id"],
        user_prompt=f"Gather context for: {task_info['name']}"
    )

    # Prior context automatically injected in result["context"]
    # Agent reads it and incorporates into discovery process
    prior_findings = result["context"]  # e.g., "Prior findings: JWT patterns found in auth/jwt.py..."

    # Perform existing research (codebase scans, pattern detection)
    discovered_context = perform_codebase_research(task_file_path)

    # Record discoveries as messages (SimpleMem-Cross heuristic extractor will identify "discovered", "found", etc.)
    await orch.record_message(
        result["memory_session_id"],
        f"Discovered patterns in {discovered_context['modules']}: {discovered_context['patterns']}"
    )

    # Finalize session: observations extracted, stored, vectorized
    report = await orch.stop_session(result["memory_session_id"])
    # e.g., report.observations_count = 3 (decisions about which patterns to include)

    # Write context manifest to task file (existing logic)
    write_context_manifest(task_file_path, discovered_context)

    await orch.end_session(result["memory_session_id"])
    orch.close()
```

**Concrete API calls grounded in research entry:**
- `create_orchestrator(project="...", tenant_id="...", max_context_tokens=2000)` — line 260-266 of research entry
- `await orch.start_session(content_session_id=..., user_prompt=...)` — line 203-206
- `result["context"]` — line 208, context automatically injected
- `await orch.record_message(...)` — line 211
- `await orch.stop_session(...)` — line 220, triggers observation extraction
- `await orch.end_session(...)` — line 223

---

## Utilization 2: implement-feature skill → SimpleMem-Cross task execution memory

**Research entry**: ./research/context-management/simplemem-cross.md
**Caller**: ./plugins/python3-development/skills/implement-feature/SKILL.md
**Integration mechanism**: Python async library + HTTP REST API (for agent communication tracking)
**Replaces or adds**: Adds persistent execution memory across task loops — currently no record of which agents were delegated tasks, what decisions they made, or patterns they followed
**Setup cost**: High (requires task loop refactoring to call SimpleMem-Cross, hook script integration for event recording, HTTP endpoint exposure for agent discovery)
**Integration surface**: `cross.orchestrator.create_orchestrator()`, `await orch.record_tool_use()`, `await orch.stop_session()`, HTTP endpoints `/cross/search`, `/cross/sessions/{id}/tool-use`

### Why this caller

The implement-feature skill loops through ready tasks, delegates each to an agent, and relies on hooks to update status. SimpleMem-Cross would:

1. Record each agent delegation as a "tool use" event (`record_tool_use(tool_name="delegate_agent", tool_input={agent, task, skills}, tool_output={result})`)
2. Auto-extract learnings when the task completes (heuristic extractor identifies agent-generated decisions: "decided to use X pattern")
3. Search across prior feature implementations to recommend agents, skills, or patterns for future tasks

**Current gap**: When `implement-feature` loops through tasks, there is no record of which agents succeeded, which patterns they adopted, or what decisions shaped the implementation. If a future feature requires similar tasks, the same pattern-selection must happen again. SimpleMem-Cross' observation extraction would surface "Agent X chose pattern Y because Z" automatically, enabling pattern-based task routing for future features.

### Integration sketch

```python
# Pseudocode: implement-feature skill loop with SimpleMem-Cross

from cross.orchestrator import create_orchestrator
import asyncio

async def implement_feature_loop(task_file_path):
    plan_id = extract_plan_id(task_file_path)  # e.g., "P3"
    feature_slug = extract_feature_slug(task_file_path)  # e.g., "integrate-sam"

    # Initialize SimpleMem-Cross for this feature
    orch = create_orchestrator(
        project="claude-skills",
        tenant_id=f"feature-{feature_slug}",
        max_context_tokens=3000
    )

    # Start session: auto-inject patterns from similar past features
    result = await orch.start_session(
        content_session_id=f"implement-{feature_slug}",
        user_prompt=f"Execute feature: {feature_slug}"
    )

    prior_patterns = result["context"]  # e.g., "Prior features used python-cli-architect for similar tasks"

    # Main implementation loop (existing)
    while True:
        # Query ready tasks
        ready = sam_ready(plan_id)
        if not ready["ready_tasks"]:
            break

        for task in ready["ready_tasks"]:
            task_id = task["id"]
            agent_name = task["agent"]

            # Record task delegation as a tool use
            await orch.record_tool_use(
                result["memory_session_id"],
                tool_name="delegate_agent",
                tool_input={
                    "task_id": task_id,
                    "agent": agent_name,
                    "skills": task.get("skills", []),
                    "dependencies": task.get("dependencies", [])
                },
                tool_output={"status": "delegated"}
            )

            # Delegate task (existing logic: Skill(skill="start-task", args=...))
            delegate_to_agent(agent_name, task_file_path, task_id)

            # Hook updates task status (existing)
            # SimpleMem-Cross will auto-capture agent's decisions via record_message below

            # Record agent result/learning
            task_result = get_task_result(task_id)
            if task_result.decision or task_result.learning:
                await orch.record_message(
                    result["memory_session_id"],
                    f"Agent {agent_name} decided: {task_result.decision}"
                )

    # Finalize: observations extracted (decisions, learnings, discoveries)
    report = await orch.stop_session(result["memory_session_id"])
    # e.g., {
    #   "observations_count": 5,
    #   "entries_stored": 5,
    #   "summary": "Feature integrated SAM schema using python-cli-architect..."
    # }

    # Search for similar prior implementations (optional post-feature analysis)
    similar = await orch.search(
        query=f"features with pattern={prior_patterns}",
        max_results=3
    )

    await orch.end_session(result["memory_session_id"])
    orch.close()

    return report
```

**Concrete API calls grounded in research entry:**
- `create_orchestrator(...)` — line 260-266
- `await orch.start_session(...)` — line 203-206
- `await orch.record_tool_use(tool_name=..., tool_input=..., tool_output=...)` — line 212-217
- `await orch.record_message(...)` — line 211
- `await orch.stop_session(...)` — line 220
- HTTP `/cross/search` endpoint — line 240

---

## Utilization 3: task_status_hook.py → SimpleMem-Cross lifecycle event recording

**Research entry**: ./research/context-management/simplemem-cross.md
**Caller**: ./plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py
**Integration mechanism**: Python async library (pip dependency)
**Replaces or adds**: Adds persistent audit trail of task lifecycle events — currently task status updates are recorded locally to task files only, not persisted across sessions
**Setup cost**: Medium (async subprocess integration in hook script, context file extension to include memory_session_id)
**Integration surface**: `cross.orchestrator.create_orchestrator()`, `await orch.record_message()`, `await orch.record_tool_use()`

### Why this caller

The task_status_hook.py script receives two hook events:
1. **SubagentStop**: Task completed, status set to COMPLETE, Completed timestamp added
2. **PostToolUse**: Write/Edit/Bash tool used, LastActivity timestamp updated

SimpleMem-Cross would record these lifecycle events, creating a persistent timeline of when tasks started, progressed, and completed across features. This enables:

- **Execution pattern analysis**: "Task T1 typically takes 2-5 hours; T2 is fast (15-30 min)"
- **Blocker detection**: "Tasks marked BLOCKED often involve auth; prior feature found workaround at path X"
- **Agent performance tracking**: "Agent Y completes similar tasks 20% faster than Agent X"

**Current gap**: Task lifecycle data is local to individual task files. After a feature completes, there is no persistent record connecting task execution patterns, agent performance, or decision timing. SimpleMem-Cross' event collection (line 72-80: 3-tier redaction, thread-safe queue) would preserve this timeline and make it available for future task routing decisions.

### Integration sketch

```python
# Pseudocode: task_status_hook.py extensions with SimpleMem-Cross

import asyncio
from cross.orchestrator import create_orchestrator
from datetime import datetime, UTC

# Global orchestrator (singleton per session)
_memory_orch = None

def get_memory_orchestrator():
    global _memory_orch
    if not _memory_orch:
        _memory_orch = create_orchestrator(
            project="claude-skills",
            tenant_id="task-execution",
            db_path="~/.simplemem-cross/task_execution.db"
        )
    return _memory_orch

async def handle_subagent_stop(hook_input):
    """Handle SubagentStop event: task completed."""
    task_file_path, task_id = extract_task_info_from_args(hook_input["args"])
    if not task_file_path or not task_id:
        return

    # Get the memory session ID from context file (written by /start-task)
    context_file = Path(".claude/context") / f"active-task-{SESSION_ID}.json"
    memory_session_id = None
    if context_file.exists():
        ctx = json.loads(context_file.read_text())
        memory_session_id = ctx.get("memory_session_id")

    # Record task completion
    orch = get_memory_orchestrator()
    if memory_session_id:
        await orch.record_message(
            memory_session_id,
            f"Task {task_id} completed at {datetime.now(UTC).isoformat()}"
        )

    # Update task status in sam (existing logic)
    sam_update_status(task_file_path, task_id, SamTaskStatus.COMPLETE)

    # Stop session: observations extracted (task completion, decisions made during task)
    if memory_session_id:
        report = await orch.stop_session(memory_session_id)
        # observations_count includes auto-detected task completion insights

async def handle_post_tool_use(hook_input):
    """Handle PostToolUse event: Write/Edit/Bash used during task."""
    # Read context file to get memory_session_id
    context_file = Path(".claude/context") / f"active-task-{SESSION_ID}.json"
    if not context_file.exists():
        return

    ctx = json.loads(context_file.read_text())
    memory_session_id = ctx.get("memory_session_id")

    if memory_session_id:
        orch = get_memory_orchestrator()

        # Record tool use with redaction (SimpleMem-Cross applies Tier 1-3 redaction)
        await orch.record_tool_use(
            memory_session_id,
            tool_name=hook_input["tool_name"],  # "Write", "Edit", "Bash"
            tool_input=hook_input["tool_input"],  # auto-redacted by SimpleMem-Cross
            tool_output=hook_input.get("tool_output", "")
        )

        # Update LastActivity in task (existing logic)
        update_last_activity(...)

# Async wrapper for hook entry point
def handle_hook(hook_input):
    """Synchronous hook entry point."""
    if hook_input["event"] == "SubagentStop":
        asyncio.run(handle_subagent_stop(hook_input))
    elif hook_input["event"] == "PostToolUse":
        asyncio.run(handle_post_tool_use(hook_input))
```

**Concrete API calls grounded in research entry:**
- `create_orchestrator(...)` — line 260-266
- `await orch.record_message(...)` — line 211
- `await orch.record_tool_use(...)` — line 212-217 (automatic redaction: Tier 1-3, line 73-80)
- `await orch.stop_session(...)` — line 220, triggers observation extraction

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| ./plugins/agent-orchestration/skills/ | Agent orchestration skill manages delegation routing but does not integrate with task lifecycle hooks or memory session management. SimpleMem-Cross memory would complement the skill, but integration requires hook registration at the skill level (outside scope of skill invocation). Deferred to backlog as a separate integration task. |

---

## Integration Summary

SimpleMem-Cross provides three concrete integration opportunities:

1. **Context-gathering agent** benefits from cross-session discovery memory, reducing redundant codebase research
2. **Implement-feature skill** gains persistent execution memory, enabling pattern-based task routing and agent performance tracking
3. **Task_status_hook.py** augments local lifecycle tracking with cross-session audit trails, supporting execution analysis

All three require pip dependency (`simplemem[cross]`), async integration, and context manifest serialization. Combined setup cost is high, but benefits compound: as features accumulate, cross-session memory accelerates both discovery and execution phases.

