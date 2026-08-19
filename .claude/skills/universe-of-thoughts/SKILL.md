---
name: universe-of-thoughts
description: Creative reasoning framework for ill-defined problems where conventional solutions are suboptimal. Use when the problem has ambiguous goals, vast solution space, no single correct answer, or requires innovation. Implements three paradigms — combinational (novel combinations of familiar ideas), exploratory (expand solution space boundaries), transformative (alter fundamental constraints). Do not use for well-defined problems, mathematical puzzles, or tasks requiring convergent reasoning.
user-invocable: true
---

# Universe of Thoughts (UoT)

Creative reasoning framework based on Margaret Boden's cognitive science theory of creativity. Implements three paradigms that build sequentially: Combinational → Exploratory → Transformative.

## When to Use

Use UoT when ANY of the following are true:

- Problem has ambiguous or undefined goals
- Solution space is vast and open-ended
- No single "correct" answer exists
- Conventional approaches have failed or are known to be suboptimal
- Task requires genuine innovation, not optimization
- Domain involves strategy, design, research direction, or policy

## When NOT to Use

Do not use UoT for:

- Well-defined problems with verifiable solutions
- Mathematical or logical puzzles (use Chain-of-Thought)
- Tasks requiring convergent reasoning toward a known answer
- Optimization within fixed constraints
- Fact retrieval or factual accuracy tasks (use Chain-of-Verification)

## Paradigm Selection

| Paradigm           | Condition                                           | Output                                      |
| ------------------ | --------------------------------------------------- | ------------------------------------------- |
| **Combinational**  | Familiar elements exist but need fresh combinations | Novel hybrids from cross-domain synthesis   |
| **Exploratory**    | Current solution space feels exhausted              | Expanded boundaries, adjacent possibilities |
| **Transformative** | Constraints themselves block progress               | Redefined rules, radical departures         |

For maximum creativity, run all three sequentially. Each builds on the previous.

---

## Phase 0: Problem Decomposition

Before selecting a paradigm, decompose the problem:

```
PROBLEM ANALYSIS:
├── Core Challenge: [What fundamentally needs solving]
├── Explicit Constraints: [Stated rules and limits]
├── Implicit Assumptions: [Unstated rules being assumed]
├── Current Domain: [Primary field this belongs to]
├── Adjacent Domains: [Related fields that might offer insight]
└── Success Criteria: [How to recognize a creative solution]
```

---

## Paradigm 1: Combinational (C-UoT)

Goal: Generate novel combinations of existing ideas by connecting previously unrelated concepts.

### C1: Domain Mapping

Identify 3-5 domains analogous to the problem domain:

```
HOME DOMAIN: [Problem's primary field]
ANALOGOUS DOMAINS:
├── [Domain A] - [Why analogous]
├── [Domain B] - [Why analogous]
├── [Domain C] - [Why analogous]
└── [Domain D] - [Why analogous]
```

### C2: Concept Extraction

For each analogous domain:

```
DOMAIN: [Name]
├── Key Mechanisms: [How it works]
├── Solved Problems: [What challenges it addresses]
└── Transferable Elements: [What could apply to target problem]
```

### C3: Cross-Domain Synthesis

Generate combinations systematically:

```
COMBINATION: [Domain A concept] + [Domain B concept]
├── Mechanism: [How they work together]
├── Application: [How this addresses the problem]
└── Assessment: [Feasibility and novelty]
```

### C4: Output

Produce 3-5 combinational solutions ranked by feasibility and novelty.

---

## Paradigm 2: Exploratory (E-UoT)

Goal: Discover new possibilities by probing the boundaries of the current solution space.

### E1: Map Current Space

```
CURRENT SOLUTION SPACE:
├── Known Approaches: [Existing solutions]
├── Common Patterns: [What they share]
├── Boundaries: [Where exploration stops]
└── Implicit Limits: [Unstated constraints on exploration]
```

### E2: Boundary Probing

For each boundary:

```
BOUNDARY: [Description]
├── What defines this limit?
├── What lies immediately beyond?
├── Is this boundary real or assumed?
└── What solution exists at/past the edge?
```

### E3: Novel Thought Generation

```
NEW THOUGHT:
├── Description: [The new idea]
├── Relationship to Existing: [How it connects to known solutions]
├── Space Extension: [How it expands possibilities]
└── Integration Potential: [Can it combine with existing solutions]
```

### E4: Output

Produce 3-5 exploratory solutions that extend beyond current boundaries while respecting immutable constraints.

---

## Paradigm 3: Transformative (T-UoT)

Goal: Alter fundamental rules or constraints to enable radically new solutions.

### T1: Constraint Archaeology

For each constraint:

```
CONSTRAINT: [Statement]
├── Origin: [Why this rule exists]
├── Type:
│   ├── Physical law → Immutable
│   ├── Regulatory → Potentially changeable
│   ├── Convention → Questionable
│   └── Assumption → Likely unnecessary
├── Removal Impact: [What happens without it]
└── Transformation Potential: [How it could be modified]
```

### T2: Rule Transformation

For constraints marked questionable or unnecessary:

```
TRANSFORMATION:
├── Original Rule: [The constraint]
├── Transformation Type: [Inversion | Relaxation | Substitution | Elimination]
├── New Rule: [The modified version]
└── New Possibilities: [What becomes possible]
```

### T3: Radical Solution Generation

```
TRANSFORMATIVE SOLUTION:
├── Rule Changes Required: [What must be different]
├── Mechanism: [How it works in the new space]
├── Implementation Path: [How to get from current state to new state]
├── Risk Assessment: [What could go wrong]
└── Reward Assessment: [Potential upside]
```

### T4: Output

Produce 2-3 transformative solutions with explicit rule changes and implementation paths.

---

## Integration: Full Pipeline

When running all three paradigms:

1. Execute C-UoT → Select top 2 solutions
2. Execute E-UoT starting from C-UoT outputs → Select top 2 solutions
3. Execute T-UoT starting from E-UoT outputs → Select top 2 solutions
4. Produce tiered portfolio:

```
SOLUTION PORTFOLIO:
├── Tier 1 (Low risk, moderate novelty): [Combinational solutions]
├── Tier 2 (Medium risk, high novelty): [Exploratory solutions]
└── Tier 3 (High risk, breakthrough potential): [Transformative solutions]
```

---

## Evaluation Criteria

Assess all solutions on the dimensions below:

| Dimension       | Question                                   | Scale     |
| --------------- | ------------------------------------------ | --------- |
| **Feasibility** | Does it violate immutable constraints?     | Pass/Fail |
| **Utility**     | How effectively does it solve the problem? | 1-10      |
| **Novelty**     | How different from existing approaches?    | 1-10      |

Solutions must pass feasibility. Rank passing solutions by (Utility × Novelty).

---

## Example: Single-Lane Bridge Traffic

**Problem**: Minimize vehicle delay on a single-lane bridge. No new bridges permitted.

### Combinational

| Source Domain       | Concept           | Application                         |
| ------------------- | ----------------- | ----------------------------------- |
| Air traffic control | Scheduled slots   | Time-slot reservations for vehicles |
| Packet switching    | Dynamic routing   | Priority-based direction changes    |
| Tidal systems       | Periodic reversal | Time-based directional flow         |

### Exploratory

| Boundary                 | Probe                             | Solution                             |
| ------------------------ | --------------------------------- | ------------------------------------ |
| Vehicles are independent | What if they communicated?        | Convoy formation, platooning         |
| Bridge is passive        | What if it signaled?              | Smart bridge with dynamic indicators |
| Optimize for fairness    | What if throughput mattered more? | Batch processing by direction        |

### Transformative

| Constraint  | Type       | Transformation        | Solution                           |
| ----------- | ---------- | --------------------- | ---------------------------------- |
| Single lane | Convention | Virtual lanes         | Motorcycle/bicycle parallel path   |
| Vehicles    | Assumption | Move people, not cars | Pedestrian/bike priority + parking |
| Bridge      | Assumption | Challenge "crossing"  | Cable car, ferry, tunnel           |

---

## References

- Suzuki & Banaei-Kashani (2025). "Universe of Thoughts: Enabling Creative Reasoning with Large Language Models." arXiv:2511.20471
- Boden, M. A. (2004, 2007, 2009). Computational creativity theory
