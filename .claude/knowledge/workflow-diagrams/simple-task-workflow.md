# Simple Task Workflow

Minimal path for straightforward tasks that don't require full orchestration complexity.

---

## Overview

Not every task requires the full 6-stage workflow. Simple tasks can follow a streamlined path while still maintaining quality.

```mermaid
flowchart LR
    INPUT["Input"]
    EXECUTE["Execute"]
    VERIFY["Verify"]
    OUTPUT["Output"]

    INPUT --> EXECUTE --> VERIFY --> OUTPUT
```

---

## When to Use Simple Workflow

```mermaid
flowchart TD
    START["New task arrives"]

    Q1{"Single, clear<br/>deliverable?"}
    Q2{"No research<br/>needed?"}
    Q3{"No delegation<br/>required?"}
    Q4{"Familiar<br/>domain?"}

    SIMPLE["→ Simple Workflow"]
    FULL["→ Full Workflow"]

    START --> Q1
    Q1 -->|"Yes"| Q2
    Q1 -->|"No"| FULL
    Q2 -->|"Yes"| Q3
    Q2 -->|"No"| FULL
    Q3 -->|"Yes"| Q4
    Q3 -->|"No"| FULL
    Q4 -->|"Yes"| SIMPLE
    Q4 -->|"No"| FULL
```

**Simple Task Criteria:**

- Single, well-defined deliverable
- No context gathering needed
- No sub-agent delegation
- Familiar technology/patterns
- Clear acceptance criteria

---

## Simple Task Flow

```mermaid
flowchart TB
    subgraph INPUT["1. INPUT"]
        I1["Receive request"]
        I2["Confirm understanding"]
    end

    subgraph EXECUTE["2. EXECUTE"]
        E1["Implement solution"]
        E2["Use tools directly"]
    end

    subgraph VERIFY["3. VERIFY"]
        V1["Check deliverable"]
        V2["Run /dh:verify-done if needed"]
    end

    subgraph OUTPUT["4. OUTPUT"]
        O1["Present result"]
        O2["Commit if appropriate"]
    end

    INPUT --> EXECUTE --> VERIFY --> OUTPUT
```

---

## Detailed Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator

    U->>O: Simple request
    O->>O: Confirm: Single deliverable?
    O->>O: Confirm: No research needed?
    O->>O: Confirm: Familiar domain?

    alt All Yes
        Note over O: Simple Workflow
        O->>O: Execute directly
        O->>O: Quick verify
        O->>U: Deliver result
    else Any No
        Note over O: Full Workflow
        O->>O: Use full 6-stage process
    end
```

---

## Assets Used in Simple Workflow

| Stage   | Required         | Optional                                 |
| ------- | ---------------- | ---------------------------------------- |
| Input   | -                | /sessions (if session management needed) |
| Execute | Direct tool use  | -                                        |
| Verify  | Quick self-check | /dh:verify-done, /am-i-complete                  |
| Output  | Present result   | git-commit-helper                        |

**Minimal Asset Path:**

```text
Input → [Direct Execution] → Quick Check → Output
```

**Enhanced Asset Path:**

```text
Input → [Direct Execution] → /dh:verify-done → git-commit-helper → Output
```

---

## Example Simple Tasks

### Example 1: Fix Typo

```mermaid
flowchart LR
    A["User: Fix typo<br/>in README"]
    B["Read file"]
    C["Edit file"]
    D["Present fix"]

    A --> B --> C --> D
```

**No extra assets needed.** Direct execution is sufficient.

### Example 2: Add Function

```mermaid
flowchart LR
    A["User: Add helper<br/>function"]
    B["Read context"]
    C["Write function"]
    D["Quick verify"]
    E["Present code"]

    A --> B --> C --> D --> E
```

**Optional:** Use `/dh:verify-done` before presenting if function is non-trivial.

### Example 3: Update Config

```mermaid
flowchart LR
    A["User: Update config<br/>value"]
    B["Read config"]
    C["Edit value"]
    D["Validate format"]
    E["Present change"]

    A --> B --> C --> D --> E
```

**No extra assets needed.** Format validation is direct.

---

## Escalation Triggers

Switch to full workflow if:

```mermaid
flowchart TD
    SIMPLE["Simple workflow<br/>in progress"]

    T1["Unexpected complexity<br/>discovered"]
    T2["Research becomes<br/>necessary"]
    T3["Multiple deliverables<br/>emerge"]
    T4["Delegation would<br/>help"]

    FULL["Switch to<br/>Full Workflow"]

    SIMPLE --> T1 --> FULL
    SIMPLE --> T2 --> FULL
    SIMPLE --> T3 --> FULL
    SIMPLE --> T4 --> FULL
```

**Escalation Indicators:**

- "I need to research this first"
- "This requires multiple steps"
- "An agent would handle this better"
- "I'm uncertain about the approach"

---

## Quality Gates for Simple Tasks

Even simple tasks need minimal verification:

```mermaid
flowchart TD
    COMPLETE["Task appears<br/>complete"]

    G1{"Deliverable<br/>matches request?"}
    G2{"No obvious<br/>errors?"}
    G3{"Would I be<br/>satisfied as user?"}

    DONE["✅ Deliver"]
    REVIEW["⚠️ Review again"]

    COMPLETE --> G1
    G1 -->|"Yes"| G2
    G1 -->|"No"| REVIEW
    G2 -->|"Yes"| G3
    G2 -->|"No"| REVIEW
    G3 -->|"Yes"| DONE
    G3 -->|"No"| REVIEW
```

---

## Simple vs Full Workflow Comparison

| Aspect            | Simple Workflow                    | Full Workflow        |
| ----------------- | ---------------------------------- | -------------------- |
| Stages            | 4 (Input, Execute, Verify, Output) | 6 (all stages)       |
| Context Gathering | None                               | Dedicated phase      |
| Planning          | Implicit                           | Explicit with skills |
| Delegation        | None                               | Available            |
| Verification      | Quick check                        | Full verify skill    |
| Assets Used       | 0-2                                | Multiple             |
| Typical Duration  | Short                              | Varies               |

---

## Decision Matrix

| Task Type           | Workflow | Reason                          |
| ------------------- | -------- | ------------------------------- |
| Fix typo            | Simple   | Single edit, no research        |
| Add simple function | Simple   | Clear scope, familiar pattern   |
| Refactor module     | Full     | Multiple files, needs planning  |
| Debug issue         | Full     | Investigation required          |
| New feature         | Full     | Decomposition needed            |
| Update config value | Simple   | Single change, clear target     |
| Create test suite   | Full     | Multiple files, planning needed |

---

## Common Patterns

### Pattern: Quick Edit

```text
1. Read target file
2. Make edit
3. Present change
```

### Pattern: Add Small Component

```text
1. Read existing code for context
2. Write new component
3. Quick verify syntax/patterns
4. Present result
```

### Pattern: Configuration Change

```text
1. Read current config
2. Make change
3. Validate format
4. Present updated config
```

---

## Navigation

- **Previous:** [Asset Decision Tree](./asset-decision-tree.md)
- **Next:** [Investigation Workflow](../../../plugins/scientific-method/shared/investigation-workflow.md)
- **Back to:** [Index](./README.md)
