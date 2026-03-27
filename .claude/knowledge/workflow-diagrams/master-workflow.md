# Master Workflow Overview

Complete visualization of the 6-stage agentic workflow with all repository assets mapped.

---

## High-Level Flow

```mermaid
flowchart TB
    subgraph INPUT["1. INPUT RECEPTION ⚠️"]
        I1[User Request]
        I2["/sessions command"]
        I3["session-start-rtica.cjs hook"]
    end

    subgraph CONTEXT["2. CONTEXT GATHERING ✅"]
        C1["context-gathering agent"]
        C2["context-refinement agent"]
        C3["/dh:rt-ica skill"]
        C4["Reference Skills<br/>(4 skills)"]
    end

    subgraph PLANNING["3. PLANNING ✅"]
        P1["/dh:rt-ica skill"]
        P2["delegate skill"]
        P3["/how-to-delegate"]
        P4["/think command"]
        P5["scientific-method:scientific-thinking skill"]
    end

    subgraph EXECUTION["4. EXECUTION ✅"]
        E1["Specialist Agents<br/>(6 agents)"]
        E2["subagent-contract skill"]
        E3["agent-creator skill"]
    end

    subgraph VERIFICATION["5. VERIFICATION ✅"]
        V1["verify skill"]
        V2["audit skill"]
        V3["/am-i-complete"]
        V4["code-review agent"]
        V5["plugin-assessor agent"]
        V6["doc-drift-auditor agent"]
    end

    subgraph OUTPUT["6. OUTPUT DELIVERY ⚠️"]
        O1["git-commit-helper skill"]
        O2["DONE/BLOCKED signaling"]
        O3["plugin-docs-writer agent"]
        O4["logging agent"]
    end

    INPUT --> CONTEXT
    CONTEXT --> PLANNING
    PLANNING --> EXECUTION
    EXECUTION --> VERIFICATION
    VERIFICATION --> OUTPUT
    VERIFICATION -.->|"Issues found"| EXECUTION
```

---

## Detailed Stage Breakdown

### Stage 1: Input Reception ⚠️ PARTIAL

```mermaid
flowchart LR
    subgraph TRIGGER["Triggers"]
        T1["User message"]
        T2["Session start"]
        T3["Hook execution"]
    end

    subgraph ASSETS["Available Assets"]
        A1["/sessions<br/>Session management"]
        A2["session-start-rtica.cjs<br/>Auto-trigger rt-ica"]
    end

    subgraph GAPS["Identified Gaps"]
        G1["❌ Task classification"]
        G2["❌ Request routing"]
        G3["❌ Priority assignment"]
    end

    T1 --> A1
    T2 --> A2
    T3 --> A2
```

**Coverage Details:**

| Asset                  | Type    | Function                            |
| ---------------------- | ------- | ----------------------------------- |
| /sessions              | Command | Manage session state, trigger modes |
| session-start-rtica.cjs | Hook    | Auto-load rt-ica on session start   |

**Gap Analysis:** No automated classification of incoming requests. Manual determination required for task type, complexity, and routing.

---

### Stage 2: Context Gathering ✅ COVERED

```mermaid
flowchart TB
    subgraph RESEARCH["Research Phase"]
        R1["context-gathering agent<br/>Deep codebase research"]
        R2["context-refinement agent<br/>Update context manifest"]
    end

    subgraph PREREQ["Prerequisites Check"]
        P1["rt-ica skill<br/>Requirements assessment"]
    end

    subgraph REFERENCE["Reference Loading"]
        REF1["claude-skills-overview-2026"]
        REF2["claude-plugins-reference-2026"]
        REF3["claude-commands-reference-2026"]
        REF4["claude-hooks-reference-2026"]
    end

    subgraph GAP["Gaps"]
        G1["❌ Context caching"]
    end

    R1 --> R2
    P1 --> R1
    REFERENCE --> R1
```

**Coverage Details:**

| Asset                          | Type  | Function                                        |
| ------------------------------ | ----- | ----------------------------------------------- |
| context-gathering              | Agent | Research without polluting orchestrator context |
| context-refinement             | Agent | Update task context manifest with discoveries   |
| rt-ica                         | Skill | Verify prerequisites before planning            |
| claude-skills-overview-2026    | Skill | Reference for skills system                     |
| claude-plugins-reference-2026  | Skill | Reference for plugins system                    |
| claude-commands-reference-2026 | Skill | Reference for commands system                   |
| claude-hooks-reference-2026    | Skill | Reference for hooks system                      |

**Gap Analysis:** No persistent caching of gathered context across sessions.

---

### Stage 3: Planning ✅ COVERED

```mermaid
flowchart TB
    subgraph ASSESS["Assessment"]
        A1["rt-ica skill<br/>Information completeness"]
    end

    subgraph DECOMPOSE["Decomposition"]
        D1["/think command<br/>Step-back reasoning"]
        D2["scientific-method:scientific-thinking skill<br/>Hypothesis formation"]
    end

    subgraph DELEGATE["Delegation Design"]
        DEL1["delegate skill<br/>WHERE-WHAT-WHY template"]
        DEL2["/how-to-delegate<br/>Full delegation guidance"]
    end

    subgraph GAP["Gaps"]
        G1["❌ Complexity estimation"]
        G2["❌ Time/effort prediction"]
    end

    A1 --> D1
    D1 --> D2
    D2 --> DEL1
    DEL1 --> DEL2
```

**Coverage Details:**

| Asset                                  | Type    | Function                                    |
| -------------------------------------- | ------- | ------------------------------------------- |
| rt-ica                                 | Skill   | Block planning until prerequisites verified |
| delegate                               | Skill   | Quick WHERE-WHAT-WHY template               |
| /how-to-delegate                       | Command | Comprehensive delegation framework          |
| /think                                 | Command | Step-back broader perspective               |
| scientific-method:scientific-thinking  | Skill   | Hypothesis-driven approach                  |
| /step-back                             | Command | Wider view of task implications             |
| /scientific-method:scientific-thinking | Command | Activate scientific method                  |

**Gap Analysis:** No automated complexity scoring or effort estimation.

---

### Stage 4: Execution ✅ COVERED

```mermaid
flowchart TB
    subgraph SPECIALISTS["Specialist Agents"]
        S1["skill-refactorer<br/>Split large skills"]
        S2["claude-context-optimizer<br/>Improve AI docs"]
        S3["subagent-refactorer<br/>Improve agent prompts"]
        S4["subagent-generator<br/>Create new agents"]
        S5["plugin-docs-writer<br/>Generate documentation"]
        S6["context-gathering<br/>Research tasks"]
    end

    subgraph GOVERNANCE["Execution Governance"]
        G1["subagent-contract skill<br/>Role boundaries"]
        G2["DONE/BLOCKED signaling"]
    end

    subgraph CREATE["Agent Creation"]
        C1["agent-creator skill<br/>Build new specialists"]
    end

    subgraph GAP["Gaps"]
        GAP1["❌ Error recovery"]
        GAP2["❌ Rollback mechanism"]
        GAP3["❌ Retry logic"]
    end

    G1 --> SPECIALISTS
    SPECIALISTS --> G2
    C1 --> SPECIALISTS
```

**Coverage Details:**

| Asset                    | Type  | Function                                 |
| ------------------------ | ----- | ---------------------------------------- |
| skill-refactorer         | Agent | Refactor large skills into focused units |
| claude-context-optimizer | Agent | Optimize AI-facing documentation         |
| subagent-refactorer      | Agent | Improve agent prompt quality             |
| subagent-generator       | Agent | Create new agent definitions             |
| plugin-docs-writer       | Agent | Generate plugin documentation            |
| context-gathering        | Agent | Execute research tasks                   |
| subagent-contract        | Skill | Enforce role boundaries and signaling    |
| agent-creator            | Skill | Create agents with proper format         |

**Gap Analysis:** No automated error recovery, rollback, or retry mechanisms.

---

### Stage 5: Verification ✅ STRONGEST

```mermaid
flowchart TB
    subgraph SELF["Self-Assessment"]
        SA1["verify skill<br/>Pre-completion checklist"]
        SA2["/am-i-complete<br/>Completion readiness"]
        SA3["/how-confident<br/>Confidence assessment"]
    end

    subgraph AUDIT["Audit Functions"]
        AU1["audit skill<br/>Hallucination detection"]
        AU2["/audit command<br/>Verify claims"]
    end

    subgraph REVIEW["Code/Asset Review"]
        R1["code-review agent<br/>Security & quality"]
        R2["plugin-assessor agent<br/>Plugin validation"]
        R3["doc-drift-auditor agent<br/>Doc accuracy"]
    end

    subgraph GAP["Gaps"]
        G1["❌ Performance verification"]
        G2["❌ Benchmark testing"]
    end

    SA1 --> AU1
    AU1 --> R1
    R1 --> SA2
```

**Coverage Details:**

| Asset             | Type    | Function                              |
| ----------------- | ------- | ------------------------------------- |
| verify            | Skill   | Rigorous self-assessment checklist    |
| audit             | Skill   | Detect hallucinations and assumptions |
| /am-i-complete    | Command | Check completion readiness            |
| /verify           | Command | Execute verification checklist        |
| /audit            | Command | Trigger hallucination audit           |
| /how-confident    | Command | Self-assess confidence level          |
| code-review       | Agent   | Security, bugs, code quality          |
| plugin-assessor   | Agent   | Plugin structure validation           |
| doc-drift-auditor | Agent   | Documentation accuracy                |

**Gap Analysis:** No performance benchmarking or automated performance verification.

---

### Stage 6: Output Delivery ⚠️ PARTIAL

```mermaid
flowchart TB
    subgraph COMMIT["Git Operations"]
        C1["git-commit-helper skill<br/>Commit message generation"]
    end

    subgraph SIGNAL["Completion Signaling"]
        S1["DONE status<br/>Task complete"]
        S2["BLOCKED status<br/>Cannot proceed"]
    end

    subgraph DOCS["Documentation"]
        D1["plugin-docs-writer agent<br/>Generate README"]
        D2["logging agent<br/>Consolidate work logs"]
    end

    subgraph GAP["Gaps"]
        G1["❌ PR workflow"]
        G2["❌ Changelog generation"]
        G3["❌ Release notes"]
    end

    C1 --> S1
    D1 --> S1
    D2 --> S1
```

**Coverage Details:**

| Asset                            | Type  | Function                             |
| -------------------------------- | ----- | ------------------------------------ |
| git-commit-helper                | Skill | Generate descriptive commit messages |
| subagent-contract (DONE/BLOCKED) | Skill | Signal completion status             |
| plugin-docs-writer               | Agent | Generate plugin documentation        |
| logging                          | Agent | Consolidate work logs                |

**Gap Analysis:** No PR creation workflow, no automated changelog, no release note generation.

---

## Complete Asset-to-Stage Mapping

```text
┌────────────────────────────────────────┬───────┬─────────┬──────────┬───────────┬──────────────┬────────┐
│ Asset                                  │ Input │ Context │ Planning │ Execution │ Verification │ Output │
├────────────────────────────────────────┼───────┼─────────┼──────────┼───────────┼──────────────┼────────┤
│ SKILLS                                 │       │         │          │           │              │        │
│ rt-ica                                 │       │    ●    │    ●     │           │              │        │
│ delegate                               │       │         │    ●     │           │              │        │
│ verify                                 │       │         │          │           │      ●       │        │
│ audit                                  │       │         │          │           │      ●       │        │
│ scientific-method:scientific-thinking  │       │         │    ●     │     ●     │              │        │
│ agent-creator                          │       │         │          │     ●     │              │        │
│ subagent-contract                      │       │         │          │     ●     │              │   ●    │
│ git-commit-helper                      │       │         │          │           │              │   ●    │
│ *-reference-2026 x4                    │       │    ●    │          │           │              │        │
├────────────────────────────────────────┼───────┼─────────┼──────────┼───────────┼──────────────┼────────┤
│ AGENTS                                 │       │         │          │           │              │        │
│ context-gathering                      │       │    ●    │          │     ●     │              │        │
│ context-refinement                     │       │    ●    │          │           │              │        │
│ code-review                            │       │         │          │           │      ●       │        │
│ plugin-assessor                        │       │         │          │           │      ●       │        │
│ plugin-docs-writer                     │       │         │          │     ●     │              │   ●    │
│ skill-refactorer                       │       │         │          │     ●     │              │        │
│ doc-drift-auditor                      │       │         │          │           │      ●       │        │
│ context-optimizer                      │       │         │          │     ●     │              │        │
│ subagent-refactorer                    │       │         │          │     ●     │              │        │
│ subagent-generator                     │       │         │          │     ●     │              │        │
│ logging                                │       │         │          │           │              │   ●    │
├────────────────────────────────────────┼───────┼─────────┼──────────┼───────────┼──────────────┼────────┤
│ COMMANDS                               │       │         │          │           │              │        │
│ /sessions                              │   ●   │         │          │           │              │        │
│ /am-i-complete                         │       │         │          │           │      ●       │        │
│ /verify                                │       │         │          │           │      ●       │        │
│ /audit                                 │       │         │          │           │      ●       │        │
│ /how-to-delegate                       │       │         │    ●     │           │              │        │
│ /think                                 │       │         │    ●     │           │              │        │
│ /step-back                             │       │         │    ●     │           │              │        │
│ /how-confident                         │       │         │          │           │      ●       │        │
│ /rt-ica                                │       │    ●    │    ●     │           │              │        │
│ /delegate                              │       │         │    ●     │           │              │        │
│ /scientific-method:scientific-thinking │       │         │    ●     │           │              │        │
├────────────────────────────────────────┼───────┼─────────┼──────────┼───────────┼──────────────┼────────┤
│ HOOKS                                  │       │         │          │           │              │        │
│ session-start-rtica                    │   ●   │         │          │           │              │        │
├────────────────────────────────────────┼───────┼─────────┼──────────┼───────────┼──────────────┼────────┤
│ COVERAGE SCORE                         │  2/3  │   7/3   │   8/3    │    8/3    │     9/3      │  4/3   │
│ STATUS                                 │  ⚠️   │   ✅    │    ✅    │    ✅     │     ✅       │  ⚠️   │
└────────────────────────────────────────┴───────┴─────────┴──────────┴───────────┴──────────────┴────────┘

Legend: ● = Asset covers this stage
Coverage threshold: ≥3 assets = ✅ COVERED, 1-2 assets = ⚠️ PARTIAL, 0 = ❌ GAP
```

---

## Navigation

- **Next:** [Asset Decision Tree](./asset-decision-tree.md) - How to choose the right asset type
- **Back to:** [Index](./README.md)
