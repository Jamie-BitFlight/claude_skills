---
title: "Utilization Proposals: MemPalace"
---

> **Review note (2026-04-08)**: All three proposals below need comparing against Claude Code's built-in `memory: project` agent frontmatter field before proceeding. Sub-agents are normally disposable — their context is discarded after task completion. When persistence is needed, agents can be given `memory: project` which provides persistent storage at `.claude/agent-memory/{agent-name}/`. Agents with this field can be instructed on what to track in project memory via their prompt. This native mechanism addresses the same gap MemPalace targets (cross-session knowledge retention) without an external dependency. Evaluate whether MemPalace offers capabilities beyond what `memory: project` provides (e.g., semantic search across all agent memories, palace-structured retrieval, cross-agent knowledge sharing) before adopting.

---

## Utilization 1: development-harness SubagentStop hook → MemPalace storage

**Research entry**: ./research/context-management/mempalace.md
**Caller**: plugins/development-harness/hooks/SubagentStop.cjs
**Integration mechanism**: Python SDK subprocess + MCP Server
**Replaces or adds**: Creates persistent cross-session session metadata storage (currently missing; ephemeral context file deleted on hook fire)
**Setup cost**: Medium (Python SDK integration + hook coordination)
**Integration surface**: `mempalace.searcher.search_memories()`, MCP tools `mempalace_add_drawer`, `mempalace_diary_write`

### Why this caller

The development-harness plugin's SubagentStop hook fires when a subagent completes work. Currently, the hook deletes the ephemeral `.claude/context/active-task-{session_id}.json` file, discarding structured session metadata (task_id, agent_type, skills_loaded, timestamps, outcome) that accumulated during the agent's work. This is exactly the use case P1 backlog item #775 documents: "Once a session ends, there is no persistent record of which agent worked on which task, what skills were loaded, how many tool calls were made, or what the agent's final output summary was."

MemPalace's `mempalace_add_drawer` tool accepts raw content and stores it with wing/room/hall metadata — perfectly suited to storing session records as part of a room dedicated to session history (e.g., wing=project, room=session-metadata, hall=hall_events). The hook could write a structured session summary before deletion, keying on the session_id and task_id from the active task context.

### Integration sketch

```python
# In SubagentStop.cjs or a new Python wrapper called by the hook:
from mempalace.searcher import search_memories
from mempalace.mcp_server import run_mcp_server

# Before deleting active-task context:
session_data = json.load(open(".claude/context/active-task-{session_id}.json"))

# Prepare a session record for storage
session_record = f"""
Session: {session_data.get("session_id")}
Task: {session_data.get("task_id")}
Agent Type: [extracted from task file]
Completed: {datetime.now().isoformat()}
Outcome: [status from task file]
Skills Loaded: [parsed from task frontmatter]
"""

# Store via MemPalace Python API or MCP call
# Using Python SDK (no API calls):
from mempalace.palace_graph import add_to_room

add_to_room(
    wing=project_slug,
    room="session-metadata",
    hall="hall_events",
    content=session_record,
    metadata={"session_id": session_id, "task_id": task_id},
)

# Then delete the ephemeral file as normal
unlink(".claude/context/active-task-{session_id}.json")
```

---

## Utilization 2: context-gathering agent → MemPalace discovery queries

**Research entry**: ./research/context-management/mempalace.md
**Caller**: ./.claude/agents/context-gathering.md
**Integration mechanism**: Python API (searcher module)
**Replaces or adds**: Adds agent-aware discovery pre-loading (currently missing; agents do not query prior discoveries before starting work)
**Setup cost**: Low (import + API call in agent prompt)
**Integration surface**: `mempalace.searcher.search_memories()`, MCP tool `mempalace_search`

### Why this caller

The context-gathering agent's role is to gather everything needed for a task before it is worked on, preventing implementation errors. P1 backlog item #1005 describes the missing loop: "Before a task-worker starts on backlog_core/server.py, it should query something like knowledge_search(file='backlog_core/server.py') and get back discoveries from prior sessions."

MemPalace's `search_memories()` API and `mempalace_search` MCP tool enable this exactly. The context-gathering agent could, as part of its research phase (Step 2: "Research Everything"), query MemPalace for prior discoveries about the modules and files it is researching. This would surface gotchas, workarounds, and constraints discovered in prior sessions — e.g., "mount() requires keyword arg namespace=, not positional — discovered by t5-server agent during #979".

### Integration sketch

```python
# In context-gathering agent execution:
from mempalace.searcher import search_memories

# Step 2: Research Everything
files_to_research = ["backlog_core/server.py", "backlog_core/models.py", "plugins/development-harness/hooks/"]

# Before reading fresh docs, query what prior agents discovered
discoveries = {}
for file_path in files_to_research:
    prior_findings = search_memories(
        query=f"gotcha constraint issue discovered in {file_path}", palace_path="~/.mempalace/palace"
    )
    if prior_findings:
        discoveries[file_path] = prior_findings

# Include discoveries in Context Manifest
if discoveries:
    context_manifest.append(f"""
### Prior Session Discoveries

The following gotchas and constraints were discovered in prior sessions:

{format_discoveries(discoveries)}

This is critical context because it prevents repeating mistakes.
""")
```

---

## Utilization 3: code-review agent → MemPalace feedback injection into agent memory

**Research entry**: ./research/context-management/mempalace.md
**Caller**: ./.claude/agents/code-review.md
**Integration mechanism**: Python SDK + MCP Server
**Replaces or adds**: Creates agent memory feedback loop (currently missing; code review findings do not feed back to reviewed agents)
**Setup cost**: High (new agent memory subsystem + code review integration point)
**Integration surface**: `mempalace.knowledge_graph.KnowledgeGraph`, MCP tools `mempalace_kg_add`, `mempalace_diary_write`

### Why this caller

P1 backlog item #1006 documents the missing Quality → Improvement loop: "When code review finds an issue in agent-generated code, nothing feeds that back to the agent or skill that produced it. The code gets fixed, but the same agent produces the same pattern next time."

MemPalace's knowledge graph and diary tools support exactly this: recording facts (triples) with timestamps and agent-specific diaries. When code review identifies a pattern issue in an agent's work, the finding can be written to that agent's memory (as a diary entry in the agent's wing). Next time the agent runs, it loads its memory and sees the prior mistake.

This requires two parts: (1) code-review agent writes findings to MemPalace diaries keyed by agent name, (2) agents load their memory diary at startup to avoid repeating mistakes.

### Integration sketch

```python
# In code-review agent, when flagging an issue:
from mempalace.knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph()

# Record the issue fact with timeline
kg.add_triple(
    subject=f"agent:{reviewed_agent_name}",
    predicate="produces_pattern",
    object=pattern_name,
    valid_from=datetime.now().isoformat(),
)

# Also write agent diary with specific example
diary_path = f"~/.mempalace/agents/{reviewed_agent_name}.txt"
diary_content = f"""
[{datetime.now().isoformat()}] Pattern detected in code review:
Mistake: {pattern_name}
Found in: {file_path} line {line_number}
Issue: {issue_description}
Reference: PR #{pr_number}
Fix applied by: {reviewer_name}
"""

# Append to agent diary
with open(diary_path, "a") as f:
    f.write(diary_content + "\n")
```

On agent startup:

```python
# In agent initialization:
from pathlib import Path

agent_diary = Path(f"~/.mempalace/agents/{agent_name}.txt")
if agent_diary.exists():
    with open(agent_diary) as f:
        agent_memory = f.read()
    # Include in system prompt
    system_prompt += f"\n## Your Prior Mistakes (from code review):\n{agent_memory}"
```

---

## Skipped Systems

No local systems were skipped. All candidate systems identified during the surface analysis had clear integration points and benefits from MemPalace's capabilities.

---

**Entry Created**: 2026-04-08 | **Research Entry**: ./research/context-management/mempalace.md | **Assessment**: COMPLETE
