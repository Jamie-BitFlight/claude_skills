# Embedded Development Skills & Agents

This `.claude/` directory contains skills and agents tailored for embedded firmware development on nRF52 and STM32 platforms with Zigbee and FreeRTOS.

## Directory Structure

```
.claude/
├── README.md                          # This file
├── skills/
│   ├── c-embedded-standards/          # Knowledge: C standards, Zigbee, FreeRTOS
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── misra-c-rules.md
│   │       ├── zigbee-door-lock.md
│   │       └── freertos-patterns.md
│   ├── add-embedded-feature/          # Workflow: Research & planning
│   │   └── SKILL.md
│   ├── implement-embedded-feature/    # Workflow: Task execution
│   │   └── SKILL.md
│   ├── embedded-debug-tools/          # Reference: Flash & debug commands
│   │   └── SKILL.md
│   ├── zuth-test-harness/             # Reference: Zigbee certification
│   │   └── SKILL.md
│   └── ha-zigbee2mqtt-docker/         # Reference: Test environment setup
│       └── SKILL.md
└── agents/
    ├── embedded-c-developer.md        # Implementation specialist
    ├── embedded-feature-researcher.md # Discovery & research
    └── embedded-codebase-analyzer.md  # AST analysis & code tracing
```

---

## Benefits of Using Skills

| Benefit                   | Description                                                       |
| ------------------------- | ----------------------------------------------------------------- |
| **Consistency**           | Standardized task execution and output formatting across sessions |
| **Reusability**           | Structured workflows replace repeated prompt engineering          |
| **Scalability**           | Same skills work across many agents and projects                  |
| **Domain Specialization** | Expert knowledge without retraining the underlying model          |

---

## How Skills and Agents Work Together

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Request                              │
│        "Add a door lock cluster to the Zigbee device"           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code Orchestrator                      │
│                                                                  │
│  1. Identifies this is a feature addition task                   │
│  2. Invokes /add-embedded-feature skill                         │
│  3. Skill delegates to specialized agents                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   Research    │ │   Analysis    │ │   Planning    │
│    Agent      │ │    Agent      │ │    Agent      │
│               │ │               │ │               │
│ Loads skills: │ │ Loads skills: │ │ Creates tasks │
│ c-embedded-   │ │ c-embedded-   │ │ with agent    │
│ standards     │ │ standards     │ │ assignments   │
└───────────────┘ └───────────────┘ └───────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    /implement-embedded-feature                   │
│                                                                  │
│  Loops through tasks, delegating each to its assigned agent:    │
│                                                                  │
│  Task 1 ──▶ @embedded-c-developer ──▶ Uses c-embedded-standards │
│  Task 2 ──▶ @embedded-c-developer ──▶ Uses embedded-debug-tools │
│  Task 3 ──▶ @embedded-c-developer ──▶ Builds and flashes        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Practical Workflow

### 1. Define Goal in Natural Language

```
"Review the repo and add a Zigbee door lock cluster implementation"
```

### 2. Claude Selects or Creates Workflow

Claude recognizes this maps to the `/add-embedded-feature` skill and invokes it.

### 3. Skill Orchestrates Agents

The skill delegates to specialized agents:

- `@embedded-feature-researcher` - Understands the goal, finds patterns
- `@embedded-codebase-analyzer` - Traces code paths, maps dependencies
- Creates a task plan with agent assignments

### 4. Agents Execute with Skills as Sub-Routines

Each agent loads relevant skills:

- `c-embedded-standards` - MISRA-C rules, Zigbee cluster specs, FreeRTOS patterns
- `embedded-debug-tools` - Flash and debug commands

---

## User-Invocable Skills (Commands)

These skills appear in the `/` menu for direct invocation:

| Command                       | Purpose                      | When to Use       |
| ----------------------------- | ---------------------------- | ----------------- |
| `/add-embedded-feature`       | Plan a new firmware feature  | Starting new work |
| `/implement-embedded-feature` | Execute a task plan          | After planning    |
| `/embedded-debug-tools`       | Flash and debug reference    | Manual debugging  |
| `/zuth-test-harness`          | Zigbee certification testing | Pre-certification |
| `/ha-zigbee2mqtt-docker`      | Test environment setup       | Development setup |

---

## Knowledge Skills (Auto-Loaded)

These skills are loaded automatically by agents when needed:

| Skill                  | Loaded By                         | Provides                                       |
| ---------------------- | --------------------------------- | ---------------------------------------------- |
| `c-embedded-standards` | embedded-c-developer, researchers | MISRA-C rules, Zigbee specs, FreeRTOS patterns |

---

## Agents

| Agent                         | Role                 | Skills Loaded                              | Permission Mode              |
| ----------------------------- | -------------------- | ------------------------------------------ | ---------------------------- |
| `embedded-c-developer`        | Write firmware code  | c-embedded-standards, embedded-debug-tools | Full (read/write/bash)       |
| `embedded-feature-researcher` | Research & discovery | c-embedded-standards                       | acceptEdits (can write docs) |
| `embedded-codebase-analyzer`  | Code analysis        | c-embedded-standards                       | dontAsk (read-only)          |

---

## Example: Complete Feature Workflow

```bash
# Step 1: Plan the feature
/add-embedded-feature "Add Zigbee door lock cluster with PIN support"

# Claude orchestrates:
# - Research agent finds similar clusters in codebase
# - Analyzer traces integration points
# - Planner creates task file: plan/tasks-door-lock.md

# Step 2: Review the plan
cat plan/tasks-door-lock.md

# Step 3: Execute the plan
/implement-embedded-feature door-lock

# Claude orchestrates:
# - Loops through tasks
# - Delegates each to @embedded-c-developer
# - Agent uses c-embedded-standards for patterns
# - Agent uses embedded-debug-tools for flash commands
# - Updates task status as each completes

# Step 4: Verify on hardware
/embedded-debug-tools
# Use commands to flash and test
```

---

## Skill-Agent-Skill Layering

The power of this system comes from **layered delegation**:

```
User Command (Skill)
    └── Orchestrates Agents
            └── Agents Load Skills
                    └── Skills Provide Domain Knowledge
```

**Example Chain:**

```
/add-embedded-feature "door lock"
    │
    ├── Delegates to @embedded-feature-researcher
    │       └── Loads c-embedded-standards
    │               └── Reads zigbee-door-lock.md reference
    │
    ├── Delegates to @embedded-codebase-analyzer
    │       └── Traces call graphs with AST tools
    │
    └── Creates plan/tasks-door-lock.md
            │
            └── /implement-embedded-feature door-lock
                    │
                    └── Delegates to @embedded-c-developer
                            ├── Loads c-embedded-standards
                            │       ├── Follows MISRA-C patterns
                            │       └── Uses FreeRTOS patterns
                            │
                            └── Loads embedded-debug-tools
                                    └── Flashes with nrfjprog
```

---

## Creating Your Own Skills

1. **Knowledge Skill**: Put reference material in `skills/my-skill/SKILL.md` with `user-invocable: false`
2. **Workflow Skill**: Create orchestration instructions with `user-invocable: true`
3. **Agent**: Create `.claude/agents/my-agent.md` with `skills: my-skill` in frontmatter

See the workshop documentation for detailed examples and best practices.

---

## References

- Workshop: `../ai-agents-skills-for-embedded-engineers.md`
- [Claude Code Skills Documentation](https://docs.anthropic.com/en/docs/claude-code/skills)
- [Claude Code Agents Documentation](https://docs.anthropic.com/en/docs/claude-code/agents)
