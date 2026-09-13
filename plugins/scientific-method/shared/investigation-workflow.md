# Investigation Workflow

Hypothesis-driven scientific method flow for debugging, research, and root cause analysis.

---

## Overview

When facing unknown problems, pattern-matching from training data can mislead. The investigation workflow applies scientific rigor to ensure conclusions are evidence-based.

```mermaid
flowchart TB
    OBS["Observation"]
    HYP["Hypothesis"]
    PRED["Prediction"]
    EXP["Experiment"]
    VER["Verification"]
    CONC["Conclusion"]

    OBS --> HYP --> PRED --> EXP --> VER
    VER -->|"Evidence supports"| CONC
    VER -->|"Evidence contradicts"| HYP
```

---

## When to Use Investigation Workflow

```mermaid
flowchart TD
    START["Problem presented"]

    Q1{"Root cause<br/>is unknown?"}
    Q2{"Multiple possible<br/>explanations?"}
    Q3{"Previous attempts<br/>failed?"}
    Q4{"Complex system<br/>interaction?"}

    INVESTIGATE["→ Investigation Workflow"]
    SIMPLE["→ Simple/Direct Fix"]

    START --> Q1
    Q1 -->|"Yes"| INVESTIGATE
    Q1 -->|"No"| Q2
    Q2 -->|"Yes"| INVESTIGATE
    Q2 -->|"No"| Q3
    Q3 -->|"Yes"| INVESTIGATE
    Q3 -->|"No"| Q4
    Q4 -->|"Yes"| INVESTIGATE
    Q4 -->|"No"| SIMPLE
```

**Investigation Triggers:**

- Debugging unknown errors
- Performance issues
- Intermittent failures
- Unexpected behavior
- Complex refactoring decisions
- Architecture questions

---

## Scientific Method Stages

### Stage 1: Observation

```mermaid
flowchart TB
    subgraph OBSERVE["Observation Phase"]
        O1["Record exact symptoms"]
        O2["Note reproduction steps"]
        O3["Identify what changed"]
        O4["Document environment"]
    end

    subgraph AVOID["Avoid"]
        A1["❌ Jumping to solutions"]
        A2["❌ Assuming cause"]
        A3["❌ Pattern-matching"]
    end

    OBSERVE --> NEXT["Form Hypothesis"]
```

**Observation Checklist:**

- [ ] What exactly is happening?
- [ ] When did it start?
- [ ] What changed recently?
- [ ] Can it be reproduced?
- [ ] What is the exact error/behavior?

---

### Stage 2: Hypothesis Formation

```mermaid
flowchart TB
    subgraph HYPOTHESES["Hypothesis Types"]
        H0["H₀: Null Hypothesis<br/>(No effect/Default state)"]
        Ha["Hₐ: Alternative Hypothesis<br/>(Proposed explanation)"]
    end

    subgraph QUALITIES["Good Hypothesis"]
        Q1["Testable"]
        Q2["Falsifiable"]
        Q3["Specific"]
    end

    HYPOTHESES --> QUALITIES
```

**Format:**

```text
H₀: [Null hypothesis - what we'd expect normally]
Hₐ: [Alternative - our proposed explanation]
```

**Example:**

```text
H₀: The timeout is caused by normal network latency
Hₐ: The timeout is caused by a connection pool exhaustion
```

---

### Stage 3: Prediction

```mermaid
flowchart LR
    HYP["Hypothesis"]
    PRED["If Hₐ, then..."]
    TEST["Testable outcome"]

    HYP --> PRED --> TEST
```

**Prediction Format:**

```text
If Hₐ is true, then [specific, observable outcome]
```

**Example:**

```text
If connection pool exhaustion causes the timeout, then:
- Pool metrics will show 0 available connections
- New connection requests will queue
- Error rate correlates with connection count
```

---

### Stage 4: Experiment

```mermaid
flowchart TB
    subgraph EXPERIMENT["Experiment Design"]
        E1["Define exact steps"]
        E2["Identify tools needed"]
        E3["Determine success criteria"]
    end

    subgraph EXECUTE["Execution"]
        X1["Run experiment"]
        X2["Record all outputs"]
        X3["Note unexpected results"]
    end

    EXPERIMENT --> EXECUTE
```

**Tree-of-Thought Planning:**

```text
Experiment:
1. [Action 1] → Expected: [outcome]
2. [Action 2] → Expected: [outcome]
3. [Action 3] → Expected: [outcome]
```

---

### Stage 5: Verification (Chain-of-Verification)

```mermaid
flowchart TB
    subgraph VERIFY["Verification Checklist"]
        V1["Results match prediction?"]
        V2["Alternative explanations ruled out?"]
        V3["Evidence is conclusive?"]
        V4["Can be independently reproduced?"]
    end

    subgraph OUTCOME["Outcomes"]
        SUPPORT["Evidence supports Hₐ"]
        REFUTE["Evidence contradicts Hₐ"]
        INSUFFICIENT["Insufficient evidence"]
    end

    VERIFY --> SUPPORT
    VERIFY --> REFUTE
    VERIFY --> INSUFFICIENT

    REFUTE --> REVISE["Revise hypothesis"]
    INSUFFICIENT --> MORE["Gather more data"]
```

---

### Stage 6: Conclusion

```mermaid
flowchart TD
    EVIDENCE["Evidence collected"]

    REJECT["Reject H₀<br/>(Hₐ supported)"]
    FAIL["Fail to reject H₀<br/>(Hₐ not supported)"]

    ACTION1["Implement fix based on Hₐ"]
    ACTION2["Form new hypothesis"]

    EVIDENCE --> REJECT
    EVIDENCE --> FAIL

    REJECT --> ACTION1
    FAIL --> ACTION2
```

**Conclusion Formats:**

```text
Reject H₀: Evidence shows [specific findings] support Hₐ
Fail to Reject H₀: Evidence shows [specific findings] do not support Hₐ
```

---

## Assets for Investigation

```mermaid
flowchart TB
    subgraph SKILLS["Skills"]
        S1["scientific-thinking<br/>Hypothesis framework"]
        S2["rt-ica<br/>Prerequisites check"]
        S3["verify<br/>Conclusion verification"]
    end

    subgraph COMMANDS["Commands"]
        C1["/think<br/>Step-back reasoning"]
        C2["/scientific-thinking<br/>Activate method"]
    end

    subgraph AGENTS["Agents"]
        A1["context-gathering<br/>Deep research"]
        A2["doc-drift-auditor<br/>Verify documentation"]
    end
```

---

## Full Investigation Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant SK as Skills
    participant AG as Agents

    U->>O: Report problem

    Note over O: OBSERVATION
    O->>O: Record symptoms
    O->>O: Document environment

    Note over O: HYPOTHESIS
    O->>SK: Load scientific-thinking
    SK-->>O: Framework loaded
    O->>O: Form H₀ and Hₐ

    Note over O: PREDICTION
    O->>O: "If Hₐ, then..."

    Note over O: EXPERIMENT
    O->>AG: context-gathering research
    AG-->>O: Research results
    O->>O: Execute tests

    Note over O: VERIFICATION
    O->>SK: Load /dh:verify-done skill
    SK-->>O: Checklist
    O->>O: Chain-of-Verification

    Note over O: CONCLUSION
    O->>O: Reject or Fail to Reject H₀
    O->>U: Report findings with evidence
```

---

## Investigation Template

```text
## Observation
[Exact symptoms, reproduction steps, environment]

## Hypothesis
- H₀: [Null hypothesis]
- Hₐ: [Alternative hypothesis]

## Prediction
If Hₐ, then [specific, observable outcome]

## Experiment (ToT)
1. [Action] → Expected: [outcome]
2. [Action] → Expected: [outcome]
3. [Action] → Expected: [outcome]

## Verification (CoVe)
- [ ] Results match prediction?
- [ ] Alternative explanations ruled out?
- [ ] Evidence conclusive?
- [ ] Reproducible?

## Conclusion
[Reject H₀ / Fail to Reject H₀] based on [specific evidence]
```

---

## Common Anti-Patterns

| Anti-Pattern              | Problem                     | Correct Approach                      |
| ------------------------- | --------------------------- | ------------------------------------- |
| "I know this pattern"     | Bypasses investigation      | Still form and test hypothesis        |
| Solution before diagnosis | May fix wrong thing         | Complete observation first            |
| Single hypothesis         | Confirmation bias           | Consider alternatives                 |
| No verification           | May accept wrong conclusion | Always verify before concluding       |
| Vague predictions         | Can't be tested             | Make specific, observable predictions |

---

## Integration with Full Workflow

```mermaid
flowchart TB
    subgraph FULL["Full Workflow"]
        I["Input"]
        C["Context"]
        P["Planning"]
        E["Execution"]
        V["Verification"]
        O["Output"]
    end

    subgraph INVEST["Investigation"]
        OBS["Observation"]
        HYP["Hypothesis"]
        PRED["Prediction"]
        EXP["Experiment"]
        COV["Verification"]
        CONC["Conclusion"]
    end

    C --> OBS
    P --> HYP
    E --> EXP
    V --> COV

    style INVEST fill:#e3f2fd
```

Investigation slots into the full workflow:

- **Context** → Observation (gather facts)
- **Planning** → Hypothesis (form testable theory)
- **Execution** → Experiment (test theory)
- **Verification** → Conclusion (confirm findings)

---

## Navigation

- **Previous:** [Simple Task Workflow](../../../.claude/knowledge/workflow-diagrams/simple-task-workflow.md)
- **Next:** [RAG Retrieval Pattern](../../../.claude/knowledge/workflow-diagrams/rag-retrieval-pattern.md)
- **Back to:** [Index](../../../.claude/knowledge/workflow-diagrams/README.md)
