---
description: 'Plan embedded firmware features using AST-based code analysis to trace call graphs, identify touch points, and decompose into implementation tasks. Use when adding features to nRF52/STM32 firmware, planning Zigbee cluster implementations, or analyzing FreeRTOS task interactions.'
argument-hint: <feature description or existing doc path>
user-invocable: true
---

# Add Embedded Feature (Research & Planning Workflow)

Convert firmware feature requests into durable planning artifacts under the repo:

- `plan/feature-context-{slug}.md` (discovery)
- `plan/codebase-analysis-{slug}.md` (AST-based code tracing)
- `plan/architect-{slug}.md` (architecture/design spec)
- `plan/tasks-{slug}.md` (executable task plan with agents and dependencies)

<feature_request>
$ARGUMENTS
</feature_request>

---

## Orchestrator Discipline

You are an orchestrator. You coordinate work across specialized agents. Prefer delegating discovery and analysis.

| Task                | Delegate To                  | Never Do Directly    |
| ------------------- | ---------------------------- | -------------------- |
| Feature research    | @embedded-feature-researcher | Research yourself    |
| Code tracing        | @embedded-codebase-analyzer  | Grep/read yourself   |
| Architecture design | @embedded-architect          | Design yourself      |
| Task decomposition  | @embedded-task-planner       | Write tasks yourself |

---

## Phase 1: Discovery (embedded-feature-researcher)

Delegate to `embedded-feature-researcher` to understand the feature request:

```text
Task(agent="embedded-feature-researcher", prompt="Research this embedded feature request and produce plan/feature-context-{slug}.md:

Feature: $ARGUMENTS

Focus on:
- WHO: Which tasks/ISRs/clusters will interact with this
- WHAT: Functional requirements and constraints
- WHEN: Trigger conditions (events, timers, Zigbee commands)
- WHY: Problem being solved

Find similar patterns in the codebase using these searches:
- Zigbee cluster handlers: pattern 'ZB_ZCL.*handler|zb_zcl.*cb'
- FreeRTOS task patterns: pattern 'xTaskCreate|vTaskDelay'
- Peripheral drivers: pattern 'void.*_IRQHandler|HAL_.*_IRQHandler'
- State machines: pattern 'enum.*state|STATE_'

Do NOT make implementation decisions. Surface questions for resolution.")
```

Output: `plan/feature-context-{slug}.md`

---

## Phase 2: Codebase Analysis (AST-Based Tracing)

Delegate to `embedded-codebase-analyzer` to trace code paths using AST tools:

```text
Task(agent="embedded-codebase-analyzer", prompt="Analyze the codebase for implementing this feature. Produce plan/codebase-analysis-{slug}.md.

Feature context: plan/feature-context-{slug}.md

Perform these analyses:

1. CALL GRAPH ANALYSIS
   - Entry points: ISRs, task functions, Zigbee callbacks
   - Trace call chains to identify all touch points
   - Map data flow between tasks

2. SYMBOL CROSS-REFERENCE
   - Find all references to related globals/structs
   - Identify shared data requiring protection
   - Map volatile variables and their accessors

3. DEPENDENCY MAPPING
   - Header file dependencies
   - Module coupling analysis
   - Identify circular dependencies

4. MEMORY LAYOUT ANALYSIS
   - Stack usage for call chains
   - Static allocation requirements
   - RAM/Flash budget impact

Use ctags, cscope, or clang AST tools where available.
Output structured analysis to plan/codebase-analysis-{slug}.md")
```

Output: `plan/codebase-analysis-{slug}.md`

---

## Phase 3: Architecture Design (embedded-architect)

Delegate to `embedded-architect` to create the design specification:

```text
Task(agent="embedded-architect", prompt="Design architecture for this embedded feature. Produce plan/architect-{slug}.md.

Inputs:
- Feature context: plan/feature-context-{slug}.md
- Codebase analysis: plan/codebase-analysis-{slug}.md
- Project constraints: CLAUDE.md, Kconfig, CMakeLists.txt

Design must include:

1. COMPONENT DIAGRAM
   - New modules/files to create
   - Existing modules to modify
   - Interface definitions

2. TASK DESIGN (if applicable)
   - Task priority and stack size
   - Communication mechanism (queue/notification/event)
   - Timing requirements

3. DATA STRUCTURES
   - New structs/enums
   - Attribute definitions (for Zigbee)
   - State machine states

4. MEMORY BUDGET
   - Flash estimate (code + const)
   - RAM estimate (stack + heap + static)
   - Constraints check

5. INTERFACE CONTRACTS
   - Function signatures
   - Callback prototypes
   - Error handling strategy

Output to plan/architect-{slug}.md")
```

Output: `plan/architect-{slug}.md`

---

## Phase 4: Task Decomposition (embedded-task-planner)

Delegate to `embedded-task-planner` to create the implementation task file:

```text
Task(agent="embedded-task-planner", prompt="Decompose the architecture into implementation tasks. Produce plan/tasks-{slug}.md.

Inputs:
- Architecture: plan/architect-{slug}.md
- Codebase analysis: plan/codebase-analysis-{slug}.md

Create tasks with this format:

## Task {N}: {Title}

**Status:** PENDING
**Priority:** P{0-2}
**Complexity:** {Low|Medium|High}
**Agent:** embedded-c-developer
**Dependencies:** [Task IDs]
**Estimated Lines:** {N}

### Description
{What to implement}

### Files to Modify
- `path/to/file.c` - {changes}
- `path/to/file.h` - {changes}

### Acceptance Criteria
- [ ] {Criterion 1}
- [ ] {Criterion 2}
- [ ] {Criterion 3}

### Verification Steps
1. Build: `west build -b {board}`
2. Flash: `west flash`
3. Test: {specific test command or manual verification}

---

Ensure tasks are ordered with dependencies respected.
Infrastructure tasks (types, headers) before implementation.
Tests after implementation.

Output to plan/tasks-{slug}.md")
```

Output: `plan/tasks-{slug}.md`

---

## Phase 5: Plan Validation

Before returning to user, validate the plan:

```text
Validate the generated plan files:

1. Check plan/tasks-{slug}.md exists and has tasks
2. Verify dependency graph has no cycles
3. Confirm all modified files from codebase-analysis are covered
4. Check memory estimates are within budget
5. Verify acceptance criteria are testable

If validation fails, report specific issues for resolution.
```

---

## Success Outcome

When all phases complete, provide the user:

```text
================================================================================
                    EMBEDDED FEATURE PLAN READY
================================================================================

Feature: {description}
Slug: {slug}

Plan Files Created:
- Discovery: plan/feature-context-{slug}.md
- Analysis: plan/codebase-analysis-{slug}.md
- Architecture: plan/architect-{slug}.md
- Tasks: plan/tasks-{slug}.md

Summary:
- Total tasks: {N}
- Estimated lines of code: {N}
- Memory impact: {N} bytes Flash, {N} bytes RAM
- Dependencies: {critical dependencies}

Questions Requiring Resolution:
1. {Question from discovery phase}
2. {Question from discovery phase}

Next Steps:
1. Review plan files and answer questions
2. Run `/implement-embedded-feature {slug}` to begin implementation
================================================================================
```

---

## AST Analysis Tools Reference

### Using ctags for Call Graph

```bash
# Generate tags
ctags -R --c-kinds=+p --fields=+S --extras=+q src/

# Find function definitions
grep "^function_name" tags

# Find callers (requires cscope)
cscope -d -L3 function_name
```

### Using cscope for Cross-Reference

```bash
# Build cscope database
find src -name "*.c" -o -name "*.h" > cscope.files
cscope -b -q -k

# Query commands:
# -L0 symbol: Find symbol
# -L1 symbol: Find global definition
# -L2 symbol: Find functions called by
# -L3 symbol: Find functions calling
```

### Using clang for AST Analysis

```bash
# Dump AST
clang -Xclang -ast-dump -fsyntax-only src/main.c

# Generate call graph
clang -S -emit-llvm src/main.c -o - | opt -dot-callgraph
```

---

## Related Skills

- `/implement-embedded-feature` - Execute tasks from plan
- `/embedded-debug-tools` - Flash and debug commands
- `/c-embedded-standards` - C coding standards reference
