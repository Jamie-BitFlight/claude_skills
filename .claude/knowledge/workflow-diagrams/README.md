# Agentic Workflow Decision Trees & Coverage Diagrams

Visual documentation mapping repository assets (skills, agents, commands, hooks) against standard agentic process flows.

---

## Quick Navigation

| Diagram                                                                                       | Purpose                                   | Use When                                 |
| --------------------------------------------------------------------------------------------- | ----------------------------------------- | ---------------------------------------- |
| [Master Workflow](./master-workflow.md)                                                       | Complete 6-stage overview with all assets | Understanding the full system            |
| [Asset Decision Tree](./asset-decision-tree.md)                                               | Skill vs Command vs Agent vs Hook         | Choosing the right extension type        |
| [Multi-Agent Orchestration](./multi-agent-orchestration.md)                                   | Delegation and DONE/BLOCKED signaling     | Coordinating specialist agents           |
| [Simple Task Workflow](./simple-task-workflow.md)                                             | Minimal path for straightforward tasks    | Quick implementations                    |
| [Investigation Workflow](../../../plugins/scientific-method/shared/investigation-workflow.md) | Hypothesis-driven scientific method       | Debugging, research, root cause analysis |
| [RAG Retrieval Pattern](./rag-retrieval-pattern.md)                                           | Context augmentation flow                 | Knowledge retrieval tasks                |
| [Gap Recommendations](./gap-recommendations.md)                                               | Specs for missing capabilities            | Planning improvements                    |

---

## Coverage Legend

All diagrams use consistent visual encoding:

```text
Coverage Levels:
  ✅ COVERED (green)  - 3+ assets covering this stage
  ⚠️ PARTIAL (yellow) - 1-2 assets covering this stage
  ❌ GAP (red/grey)   - No assets, identified gap
```

### Mermaid Style Classes

```css
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e8f5e9', 'primaryBorderColor': '#4caf50'}}}%%

classDef covered fill:#c8e6c9,stroke:#4caf50,stroke-width:2px,color:#1b5e20
classDef partial fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17
classDef gap fill:#ffcdd2,stroke:#e53935,stroke-width:2px,color:#b71c1c
classDef neutral fill:#e0e0e0,stroke:#757575,stroke-width:1px,color:#424242
```

---

## Repository Asset Summary

### Skills (12 total)

| Skill                                 | Stage Coverage      | Primary Purpose                      |
| ------------------------------------- | ------------------- | ------------------------------------ |
| rt-ica                                | Input, Planning     | Pre-planning requirements checkpoint |
| delegate                              | Planning            | Sub-agent prompt template            |
| verify                                | Verification        | Pre-completion self-assessment       |
| audit                                 | Verification        | Hallucination detection              |
| scientific-method:scientific-thinking | Planning, Execution | Hypothesis-driven reasoning          |
| agent-creator                         | Execution           | Create new agents                    |
| subagent-contract                     | Execution           | Role boundaries and signaling        |
| git-commit-helper                     | Output              | Commit message generation            |
| claude-skills-overview-2026           | Context             | Skills system reference              |
| claude-plugins-reference-2026         | Context             | Plugins system reference             |
| claude-commands-reference-2026        | Context             | Commands system reference            |
| claude-hooks-reference-2026           | Context             | Hooks system reference               |

### Agents (11 total)

| Agent                    | Stage Coverage | Primary Purpose                    |
| ------------------------ | -------------- | ---------------------------------- |
| context-gathering        | Context        | Research without polluting context |
| context-refinement       | Context        | Update context manifest            |
| code-review              | Verification   | Security and quality review        |
| plugin-assessor          | Verification   | Plugin structure validation        |
| plugin-docs-writer       | Output         | Generate plugin documentation      |
| skill-refactorer         | Execution      | Split large skills                 |
| doc-drift-auditor        | Verification   | Documentation accuracy             |
| claude-context-optimizer | Execution      | Improve AI-facing docs             |
| subagent-refactorer      | Execution      | Improve agent prompts              |
| subagent-generator       | Execution      | Create new agents                  |
| logging                  | Output         | Consolidate work logs              |

### Commands (11 total)

| Command                                | Stage Coverage | Primary Purpose              |
| -------------------------------------- | -------------- | ---------------------------- |
| /am-i-complete                         | Verification   | Completion readiness check   |
| /verify                                | Verification   | Self-assessment checklist    |
| /audit                                 | Verification   | Hallucination detection      |
| /how-to-delegate                       | Planning       | Delegation guidance          |
| /think                                 | Planning       | Step-back reasoning          |
| /sessions                              | Input          | Session management           |
| /step-back                             | Planning       | Broader perspective          |
| /how-confident                         | Verification   | Confidence self-assessment   |
| /dh:rt-ica                             | Planning       | Requirements assessment      |
| /delegate                              | Planning       | Quick delegation template    |
| /scientific-method:scientific-thinking | Planning       | Scientific method activation |

### Hooks (1 total)

| Hook                    | Stage Coverage | Primary Purpose                      |
| ----------------------- | -------------- | ------------------------------------ |
| session-start-rtica.cjs | Input          | Auto-trigger rt-ica on session start |

---

## Coverage by Stage

```text
Stage 1: INPUT RECEPTION
├── Coverage: ⚠️ PARTIAL
├── Assets: /sessions, session-start-rtica.cjs
└── Gaps: No task classification, no routing

Stage 2: CONTEXT GATHERING
├── Coverage: ✅ COVERED
├── Assets: context-gathering, context-refinement, rt-ica, 4 reference skills
└── Gaps: No context caching

Stage 3: PLANNING
├── Coverage: ✅ COVERED
├── Assets: rt-ica, delegate, /how-to-delegate, /think, scientific-method:scientific-thinking
└── Gaps: No complexity estimation

Stage 4: EXECUTION
├── Coverage: ✅ COVERED
├── Assets: 6 specialist agents, subagent-contract, agent-creator
└── Gaps: No error recovery/rollback

Stage 5: VERIFICATION
├── Coverage: ✅ STRONGEST
├── Assets: verify, audit, /am-i-complete, code-review, plugin-assessor
└── Gaps: No performance verification

Stage 6: OUTPUT DELIVERY
├── Coverage: ⚠️ PARTIAL
├── Assets: git-commit-helper, DONE/BLOCKED signaling, plugin-docs-writer
└── Gaps: No PR workflow, no changelog generation
```

---

## How to Use These Diagrams

1. **New to the system?** Start with [Master Workflow](./master-workflow.md)
2. **Building an extension?** Use [Asset Decision Tree](./asset-decision-tree.md)
3. **Delegating work?** Follow [Multi-Agent Orchestration](./multi-agent-orchestration.md)
4. **Quick task?** Use [Simple Task Workflow](./simple-task-workflow.md)
5. **Debugging/research?** Follow [Investigation Workflow](../../../plugins/scientific-method/shared/investigation-workflow.md)
6. **Need context?** Use [RAG Retrieval Pattern](./rag-retrieval-pattern.md)
7. **Planning improvements?** See [Gap Recommendations](./gap-recommendations.md)

---

## Maintenance

When adding new skills, agents, commands, or hooks:

1. Update the asset tables in this README
2. Add the asset to relevant workflow diagrams
3. Update coverage assessments if stage coverage changes
4. Review gap recommendations for closure
