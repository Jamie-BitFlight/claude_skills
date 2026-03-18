# The Delegation

**Research Date**: 2026-03-18
**Source URL**: <https://arturitu.github.io/the-delegation/>
**GitHub Repository**: <https://github.com/arturitu/the-delegation>
**Version at Research**: v0.1.0
**License**: Dual-licensed — Source Code (MIT) | 3D Models & Assets (CC BY-NC 4.0)

---

## Overview

The Delegation is a high-performance 3D simulation that reimagines multi-agent collaboration by embodying LLM-powered autonomous agents in a shared physical workspace. Unlike traditional chat-only agent frameworks, agents here navigate a 3D office environment, claim workstations, express emotions through animations, and interact with the user and each other to fulfill complex project briefs. The system combines a specialized agency orchestration service with WebGPU-accelerated character instancing to enable real-time, embodied multi-agent workflows.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| **Static, chat-based agent interaction** | Embodied agents with spatial presence, emotional expression, and dynamic navigation in a shared 3D environment; users interact through a living office rather than a prompt window |
| **Limited agent coordination visibility** | Real-time Kanban board, agent inspector panels, and action logs expose the full agency workflow—including hidden LLM tool calls and task state transitions |
| **Single-agent frameworks** | Orchestrated multi-agent workflow with a Project Manager (Orchestrator) agent that assigns tasks, schedules work, and manages client approvals across a team of specialized agents |
| **AI skill/tool integration friction** | Deep LLM function calling integration with tool-augmented agents; agents directly invoke functions like `propose_task`, `request_approval`, and `complete_task` within the simulation |
| **No spatial workstation management** | Agents claim "Points of Interest" (desks, chairs, computers) via NavMesh-based pathfinding; the system ensures only one agent works at each POI at a time |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | Not publicly accessible (private repo or very new) | 2026-03-18 |
| Package Version | 0.1.0 | 2026-03-18 |
| Latest Commit | 2026-03-10 | 2026-03-18 |
| Commit Count | 1 (early development) | 2026-03-18 |
| TypeScript Source Files | 48 files | 2026-03-18 |
| Current LLM Provider | Google Gemini API (BYOK) | 2026-03-18 |

---

## Key Features

### Advanced Agency System

- **Orchestrated Workflow**: A specialized Project Manager agent (the Orchestrator) manages the project lifecycle from initial client briefing through final delivery, assigning tasks to specialized agents and coordinating approvals.
- **Autonomous Task Management**: Agents propose their own tasks, request client approval when stuck, and autonomously update a real-time Kanban board reflecting work status (scheduled, in_progress, on_hold, done).
- **Tool-Augmented Intelligence**: Deep integration with LLM function calling enables agents to invoke concrete tools within the simulation: `propose_task`, `request_client_approval`, `complete_task`, `propose_subtask`, `update_client_brief`, `notify_client_project_ready`.
- **Multi-Agent Boardroom Sessions**: When complex tasks require multiple agents, the system stages a "boardroom" meeting where each agent speaks once in round-robin fashion to propose subtasks.

### Embodied Simulation

- **Hybrid GPU/CPU Architecture**: Character rendering uses WebGPU Compute Shaders with instanced geometry for high-efficiency rendering of multiple agents; CPU handles behavior state machines and pathfinding.
- **Intelligent Pathfinding & POI System**: NPCs utilize a NavMesh-based pathfinding system (powered by [three-pathfinding](https://github.com/donmccurdy/three-pathfinding)) to navigate the 3D office and dynamically claim "Points of Interest" (desks, chairs, computers) based on their assigned task. POI system ensures workstation occupancy is exclusive.
- **Dynamic State Machine**: Characters transition through defined states (idle, walk, sit_down, sit_idle, sit_work, talk, listen, look_around) with corresponding animations. Facial expressions (idle, listening, neutral, surprised, happy, sick, wink, doubtful, sad) sync with behavior state via GPU-driven expression atlas.
- **Spatial Speech Bubbles & Real-Time Animation Sync**: 3D speech bubbles are projected into React UI overlays; character animations (walking, sitting, working, talking) remain synchronized with LLM-driven task execution.

### Interactive UI

- **Real-Time 3D Overlay**: Status indicators, interaction menus, and chat panels are projected from 3D space into the React UI without blocking the 3D viewport; users click agents in 3D to interact.
- **Agent Inspector**: Users select any agent to view their current "thoughts" (last LLM system prompt context), mission (assigned task), task history, and action logs.
- **Kanban & Action Logs**: Complete transparency into task status workflow (scheduled → in_progress → on_hold → done) and visible LLM function calls (e.g., `propose_task`, `request_approval`) with timestamps.
- **BYOK (Bring Your Own Key) Modal**: Users provide their own Gemini API key; the app runs entirely client-side with no backend required.

---

## Technical Architecture

**Core Components**:

1. **Agency Service** (`src/services/agencyService.ts`): Routes LLM calls to the Gemini API with function definitions. Manages three types of LLM calls:
   - `callOrchestrator()` — Project Manager agent
   - `callAgent()` — Individual worker agents
   - `callBoardroomAgent()` — Multi-agent boardroom session agent

2. **Agency Orchestrator Hook** (`src/hooks/useAgencyOrchestrator.ts`): Implements the workflow loop:
   - Monitors task state changes via Zustand store subscription
   - Dispatches newly-scheduled tasks to their assigned agents
   - Handles single-agent task execution and multi-agent boardroom meetings
   - Intercepts agent function calls and routes them to `ToolHandlerService`
   - Checks when all tasks complete, then triggers final delivery

3. **Tool Handler Service** (`src/services/toolHandlerService.ts`): Processes agent function calls:
   - Updates task Kanban status (scheduled, in_progress, on_hold, done)
   - Manages client approval workflow (agents halt at `request_client_approval` until user input)
   - Updates client brief when agents call `update_client_brief`
   - Removes tasks when agents delete them
   - Logs all actions to the action log for transparency

4. **Character System** (`src/three/` directory):
   - **SceneManager**: Manages the Three.js WebGPU scene, camera, lighting, and POI positions
   - **CharacterManager**: GPU character instancing with WebGPU Compute Shaders; manages animation playback from glTF bone-weighted character models
   - **NPC Drivers**: Per-agent behavior drivers (one per NPC) that handle pathfinding state, animation transitions, and POI occupation
   - **NavMesh System**: Uses `three-pathfinding` to compute paths to claimed workstations

5. **Store (Zustand)** (`src/store/`):
   - **agencyStore**: Global state for tasks, client brief, phase (idle → briefing → working → awaiting_approval → done), final output, action logs
   - **useStore**: Character visual state (selected NPC, hovered POI, screen positions for 3D-to-UI projection)
   - **useLLMConfigStore**: Gemini API key and model configuration

6. **LLM Provider** (`src/services/llm/providers/GeminiProvider.ts`): Wraps Google Gemini API v1.29.0; handles streaming responses and function calling.

**Data Flow**:

```
User provides briefing to Orchestrator
       ↓
Orchestrator parses brief, calls propose_task
       ↓
ToolHandlerService adds tasks to Kanban (status: scheduled)
       ↓
useAgencyOrchestrator detects new scheduled tasks
       ↓
For each task:
  - Assign to agent(s)
  - callAgent or callBoardroomAgent
  - Agent calls request_client_approval (or complete_task directly)
  - ToolHandlerService pauses task (on_hold) and logs
  - User reviews & responds
  - Agent resumes, calls complete_task
  - ToolHandlerService marks task done
       ↓
When all tasks done, Orchestrator calls notify_client_project_ready
       ↓
System shows final output and transitions to done phase
```

**Technology Stack**:

- **Rendering**: Three.js (WebGPU & TypeScript Shading Language) for GPU compute and advanced rendering
- **UI**: React 19 + Tailwind CSS + Motion (for animation)
- **State**: Zustand for unified reactive store bridging 3D and React
- **3D Assets**: Blender-exported glTF models with bone-weighted animations and custom expression atlas
- **Pathfinding**: three-pathfinding (NavMesh-based A* pathfinding)
- **LLM Integration**: Google Gemini API (@google/genai v1.29.0)
- **Build**: Vite (v6.2.0) + TypeScript

---

## Installation & Usage

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

Then navigate to the local URL shown (typically `http://localhost:3000/the-delegation`).

### Build for Production

```bash
npm run build
```

### Usage Workflow

1. **Provide a Client Brief**: Start with the Orchestrator agent. Type your project description (e.g., "Create a logo and brand guidelines for a new SaaS product").

2. **Orchestrator Parses & Proposes Tasks**: The Project Manager agent breaks down your brief into tasks and proposes them via the Kanban board.

3. **Assign Tasks to Agents**: The system automatically assigns tasks based on agent expertise (designer, developer, copywriter, etc.).

4. **Review & Approve**: When an agent requests approval via `request_client_approval`, you (the client) are presented with the agent's plan in a popup. You can approve or provide feedback.

5. **Monitor Progress**: Watch agents navigate the 3D office, claim desks, and work on their assigned tasks. The action log and Kanban board show all state transitions.

6. **Receive Final Output**: Once all tasks complete, the Orchestrator synthesizes team outputs and presents the final deliverable.

### Example: Minimal Agent Setup

The demo includes a default team (Designer, Developer, Copywriter, Analyst). To create custom teams, modify `src/data/agents.ts` to define agent roles and specializations. The agent inspector will display the active agent set.

---

## Relevance to Claude Code Development

### Applications

- **Embodied Multi-Agent Orchestration Patterns**: The Delegation demonstrates how to manage multi-agent workflows with explicit orchestrator coordination, task state machines, and client approval gates — patterns directly applicable to Claude Code's SAM (Structured Agent-Managed) feature implementation workflow (`/add-new-feature` → `/implement-feature` → `/complete-implementation`).
- **Tool-Augmented Agent Integration**: The system's deep LLM function calling integration (agents invoking `propose_task`, `request_approval`, etc.) mirrors the pattern of agents in Claude Code using Bash/Edit/Read tools — both require safe, idempotent tool invocation and robust error handling.
- **Spatial Workstation Management**: The POI (Point of Interest) system and NavMesh-based pathfinding solve a general resource allocation problem: ensuring only one agent works on a resource at a time. This applies to Claude Code's task-claiming logic (`sam claim P{N} {task_id}`) to prevent double-dispatch.

### Patterns Worth Adopting

- **Agency State Machine**: The explicit phase transitions (idle → briefing → working → awaiting_approval → done) provide a clear, finite-state model for project lifecycle management. Claude Code's SAM workflow could benefit from similar explicit phase state.
- **Transparent Action Logging**: Every agent action is logged with timestamp, agent index, task ID, and action description. This transparency is invaluable for debugging multi-agent workflows and understanding causality. Claude Code's `task_status_hook.py` and task file update patterns follow this principle.
- **Synchronous Approval Gates**: When an agent needs client input, it halts via `request_client_approval` and awaits explicit user response before resuming. This prevents speculative agent work and ensures human-in-the-loop control. Claude Code's `/complete-implementation` quality gates use a similar async gate pattern.
- **Real-Time Status Visualization**: The Kanban board and agent inspector provide live visibility into task state and agent context. Claude Code's task file format (with timestamps, status, and context sections) achieves similar transparency via static files.

### Integration Opportunities

- **3D Task Visualization Plugin for Claude Code**: Adapt The Delegation's React + Three.js UI to visualize Claude Code's SAM task graph in real-time — nodes for tasks, edges for dependencies, agent assignments, and status transitions.
- **Spatial Workstation Allocation for Parallel Task Execution**: Apply the POI occupancy system to Claude Code's agent dispatcher to model and prevent task collisions when multiple agents are dispatched in parallel.
- **Client Approval Workflow Automation**: Generalize The Delegation's `request_client_approval` → user-input → agent-resume pattern into a reusable skill for any Claude Code workflow that requires human checkpoints.

---

## References

- [The Delegation Repository](https://github.com/arturitu/the-delegation) (accessed 2026-03-18)
- [The Delegation Live Demo](https://arturitu.github.io/the-delegation/) (accessed 2026-03-18)
- [Three.js WebGPU Documentation](https://threejs.org/docs/#manual/en/introduction/WebGPU) (accessed 2026-03-18)
- [three-pathfinding Library](https://github.com/donmccurdy/three-pathfinding) (accessed 2026-03-18)
- [Google Gemini API Documentation](https://ai.google.dev/gemini-api/docs) (accessed 2026-03-18)
- [Zustand State Management](https://github.com/pmndrs/zustand) (accessed 2026-03-18)
- [Repository package.json](https://github.com/arturitu/the-delegation/blob/main/package.json) (accessed 2026-03-18)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Vibe Kanban](../task-management/vibe-kanban.md) | task-management | Multi-agent orchestration with Kanban board UI; mirrors The Delegation's task state visualization (scheduled → in_progress → on_hold → done) and git worktree-per-task isolation pattern |
| [CopilotKit](../agent-frameworks/copilotkit.md) | agent-frameworks | React-based agentic frontend with bi-directional state sync; both embed agents in interactive UIs with real-time state mutations and approval checkpoints |
| [Tersa](../agent-frameworks/tersa.md) | agent-frameworks | Visual node canvas for multi-step AI workflows; complements The Delegation's UI model with an alternative approach to expressing task dependency graphs and agent coordination |
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | 16-agent orchestration system with explicit chief-of-staff coordinator; demonstrates scaled multi-agent patterns similar to The Delegation's Project Manager + worker agent hierarchy |
| [Agent Deck](../developer-tools/agent-deck.md) | developer-tools | Terminal UI for managing multiple concurrent AI agent sessions; shares The Delegation's real-time status monitoring, session forking, and isolated execution (worktree/sandbox) patterns |
| [OpenHands](../coding-agents/openhands.md) | coding-agents | Multi-agent platform with task decomposition and cloud deployment; provides architectural contrast showing alternative approaches to agent coordination and workspace isolation |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-18 |
| Version at Verification | v0.1.0 |
| Next Review Recommended | 2026-06-18 |
| Confidence Map | `Overview: high (official README + demo accessible)`, `Problem Addressed: high (derived from README feature list)`, `Key Statistics: medium (v0.1.0 is very early release; star count not yet significant)`, `Key Features: high (extracted from README and package.json dependency list)`, `Technical Architecture: medium (code-read — source files inspected but entry is early-stage and architecture may evolve)`, `Installation & Usage: high (verified via README and package.json scripts)`, `Relevance to Claude Code: medium (patterns inferred from architecture; actual integration testing not yet performed)` |
