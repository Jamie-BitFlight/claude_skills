# Plugin Creator Workflow Diagram

<!-- Converted from mixed ASCII + sparse mermaid: complete agentic plugin creation workflow -->

This diagram set covers the full agentic workflow for creating Claude Code plugins.
Each diagram corresponds to a named phase in [SKILL.md](../SKILL.md).

---

## High-Level Flow

```mermaid
flowchart LR
    P0(["Phase 0<br>RT-ICA Check"])
    P05(["Phase 0.5<br>Discussion"])
    P1(["Phase 1<br>Research"])
    P2(["Phase 2<br>Design"])
    P3(["Phase 3<br>Implementation"])
    P4(["Phase 4<br>Validation"])
    P5(["Phase 5<br>Documentation"])
    P6(["Phase 6<br>Final Verification"])
    Done(["Plugin complete"])

    P0 -->|"APPROVED — all 6 conditions satisfied"| P05
    P0 -->|"BLOCKED — one or more conditions missing"| RequestInfo["Request missing info from user"]
    RequestInfo --> P0
    P05 --> P1
    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5
    P5 --> P6
    P6 -->|"All 4 checks PASS"| Done
    P6 -->|"Any check FAIL — return to phase<br>where the failing check originates"| P4
```

---

## Phase 0 — RT-ICA Prerequisite Check

```mermaid
flowchart TD
    Start(["User request received"]) --> Invoke["Invoke rt-ica skill —<br>produce RT-ICA SUMMARY with<br>6 conditions each marked<br>AVAILABLE / DERIVABLE / MISSING"]
    Invoke --> Q{"RT-ICA SUMMARY output:<br>any condition marked MISSING?"}
    Q -->|"Yes — one or more conditions<br>show MISSING"| Blocked["BLOCKED —<br>state which conditions are MISSING;<br>request that information from user"]
    Blocked --> Start
    Q -->|"No — all 6 conditions<br>are AVAILABLE or DERIVABLE"| Approved["APPROVED —<br>proceed to Phase 0.5 Discussion"]
```

---

## Phase 0.5 — Discussion (Capture Preferences)

```mermaid
flowchart TD
    Start(["APPROVED from Phase 0"]) --> Q1{"Primary plugin type?"}

    Q1 -->|"Skill-focused"| AskSkill["Ask 4 targeted questions —<br>activation triggers, tool restrictions,<br>output format, reference structure"]
    Q1 -->|"Agent-focused"| AskAgent["Ask 3 targeted questions —<br>delegation scope, return format,<br>error handling strategy"]
    Q1 -->|"Hook-focused"| AskHook["Ask 3 targeted questions —<br>trigger events, hook type,<br>timeout handling"]
    Q1 -->|"Mixed — more than one type"| AskAll["Ask all relevant question sets<br>for each type present"]

    AskSkill --> Save
    AskAgent --> Save
    AskHook --> Save
    AskAll --> Save

    Save["Save all answers to<br>.claude/plan/{plugin-name}/discuss-CONTEXT.md —<br>scope decisions, UX preferences,<br>technical choices with rationale"]
    Save --> Done(["Preferences captured —<br>proceed to Phase 1 Research"])
```

---

## Phase 1 — Research (4-Way Parallel)

```mermaid
flowchart TD
    Start(["Preferences captured from Phase 0.5"]) --> Spawn["Spawn all 4 researchers<br>in a single message — they run concurrently"]

    Spawn --> R1["Researcher 1 — subagent_type='plugin-creator:plugin-assessor'<br>Task: search plugins/ and ~/.claude/skills/ for similar functionality;<br>identify gaps and patterns to follow or avoid;<br>write to .claude/plan/{plugin-name}/research-1-existing.md"]

    Spawn --> R2["Researcher 2 — subagent_type='plugin-creator:plugin-assessor'<br>Task: identify which Claude Code features the plugin should use<br>(dynamic context, hooks, MCP/LSP, subagent execution);<br>write to .claude/plan/{plugin-name}/research-2-features.md"]

    Spawn --> R3["Researcher 3 — subagent_type='plugin-creator:plugin-assessor'<br>Task: analyze architecture patterns from well-structured plugins<br>(skill directories, reference files, agent definitions, hook configs);<br>write to .claude/plan/{plugin-name}/research-3-architecture.md"]

    Spawn --> R4["Researcher 4 — subagent_type='general-purpose'<br>Task: fetch https://code.claude.com/docs/en/plugins-reference.md<br>and https://code.claude.com/docs/en/skills.md;<br>identify schema requirements, common mistakes, deprecations;<br>write to .claude/plan/{plugin-name}/research-4-pitfalls.md"]

    R1 --> Merge
    R2 --> Merge
    R3 --> Merge
    R4 --> Merge

    Merge["Wait for all 4 to complete —<br>merge into .claude/plan/{plugin-name}/research-FINDINGS.md<br>with sections: Existing Solutions, Recommended Features,<br>Architecture Patterns, Pitfalls and Requirements, Synthesis"]
    Merge --> Done(["research-FINDINGS.md written —<br>proceed to Phase 2 Design"])
```

---

## Phase 2 — Design (Plan + Verify Loop)

```mermaid
flowchart TD
    Start(["research-FINDINGS.md written"]) --> Plan["2a — Delegate to Plan agent:<br>subagent_type='Plan'<br>Inputs: discuss-CONTEXT.md + research-FINDINGS.md<br>Output: XML task specs — each task has id, name, files,<br>action, verify command, and done criteria"]

    Plan --> Check["2b — Delegate to plan checker:<br>subagent_type='general-purpose'<br>Verify: tasks cover all required components,<br>tasks are atomic, verify commands are runnable,<br>no gaps between tasks, sequence respects dependencies"]

    Check --> Q{"Plan checker output<br>contains PASS or FAIL?"}

    Q -->|"FAIL — specific issues listed"| Fix["Return issues to Plan agent;<br>re-delegate 2a with the checker's<br>feedback as additional input"]
    Fix --> Plan

    Q -->|"PASS — no issues listed"| Save["2c — Save approved plan to<br>.claude/plan/{plugin-name}/design-PLAN.md<br>with status APPROVED and plan checker reviewer ID"]
    Save --> Done(["design-PLAN.md written —<br>proceed to Phase 3 Implementation"])
```

---

## Phase 3 — Implementation (Atomic Execution)

```mermaid
flowchart TD
    Start(["design-PLAN.md written"]) --> ScaffoldQ{"Does plugin require only standard<br>scaffold (plugin.json + one SKILL.md)<br>with no custom agents or hooks?"}

    ScaffoldQ -->|"Yes — standard scaffold only"| Script["Use scaffolding script —<br>uv run scripts/create_plugin.py create {plugin-name}<br>-d '{description}' -s {skill-name} -o ./plugins<br>Script self-validates created files"]
    ScaffoldQ -->|"No — custom agents, hooks,<br>or advanced features required"| ReadPlan["Read each XML task from design-PLAN.md<br>one at a time in dependency order"]

    Script --> AdvQ{"Advanced features required?<br>(hooks, MCP servers, dynamic context,<br>string substitutions, fork context)"}
    AdvQ -->|"No"| ValidationEntry(["Proceed to Phase 4 Validation"])
    AdvQ -->|"Yes"| ReadPlan

    ReadPlan --> DepQ{"Does this task depend on<br>output from a previous task<br>that is not yet COMPLETE?"}
    DepQ -->|"Yes — dependency not complete"| Wait["Wait for dependency task to complete<br>before spawning this task"]
    Wait --> DepQ

    DepQ -->|"No — no pending dependency"| ParallelQ{"Are there other tasks with<br>no pending dependencies?"}
    ParallelQ -->|"Yes — spawn concurrently"| SpawnMulti["Spawn multiple executor agents<br>in a single message —<br>one per ready task"]
    ParallelQ -->|"No — only this task is ready"| SpawnOne["Spawn one executor agent:<br>subagent_type='general-purpose'<br>Pass task XML with action, verify command,<br>done criteria, and context from discuss-CONTEXT.md"]

    SpawnMulti --> ExecResult
    SpawnOne --> ExecResult

    ExecResult{"Executor agent output:<br>Verification result PASS or FAIL?"}
    ExecResult -->|"PASS — done criteria met"| Commit["Atomic git commit —<br>stage only the files listed in the task's files element;<br>commit message: 'task-{N}: {task name}'"]
    ExecResult -->|"FAIL — verification failed<br>or error in implementation"| Debug["Delegate to debugger agent:<br>subagent_type='general-purpose'<br>Pass failure details + plugin path;<br>receive fix plan as XML;<br>re-execute the task with the fix applied"]
    Debug --> ExecResult

    Commit --> MoreQ{"More tasks remaining<br>in design-PLAN.md?"}
    MoreQ -->|"Yes"| ReadPlan
    MoreQ -->|"No — all tasks committed"| ValidationEntry(["All tasks complete —<br>proceed to Phase 4 Validation"])
```

---

## Phase 4 — Validation (Multi-Layer)

```mermaid
flowchart TD
    Start(["All tasks complete"]) --> L1L2["Run Layer 1 and Layer 2 in parallel"]

    L1L2 --> L1["Layer 1 — Script validation (parallel):<br>uv run scripts/create_plugin.py validate ./plugins/{plugin-name}<br>uvx skilllint@latest check ./plugins/{plugin-name}"]

    L1L2 --> L2["Layer 2 — Official docs verification:<br>subagent_type='general-purpose'<br>Fetch plugins-reference.md and skills.md;<br>compare plugin against schema requirements;<br>output PASS with all compliant, or FAIL with file:line violations"]

    L1 --> L1Q{"Layer 1 exit code = 0?"}
    L2 --> L2Q{"Layer 2 output contains PASS?"}

    L1Q -->|"Non-zero — validation errors found"| Debug
    L2Q -->|"FAIL — schema violations listed"| Debug

    L1Q -->|"0 — validation passed"| L3Wait
    L2Q -->|"PASS — all compliant"| L3Wait

    L3Wait{"Both Layer 1 and Layer 2<br>have passed?"}
    L3Wait -->|"No — waiting for the other"| L3Wait
    L3Wait -->|"Yes — both passed"| L3

    L3["Layer 3 — Quality assessment:<br>subagent_type='plugin-creator:plugin-assessor'<br>Check structural correctness, frontmatter optimization,<br>documentation completeness, cross-reference integrity;<br>output score 1-10 with specific issues listed"]

    L3 --> L3Q{"Layer 3 score >= 7<br>AND no critical issues listed?"}
    L3Q -->|"No — score < 7 or critical issues present"| Debug

    L3Q -->|"Yes — quality threshold met"| SaveReport["Save validation-REPORT.md —<br>Layer 1 status + script output,<br>Layer 2 status + compliance details,<br>Layer 3 score + issue list,<br>debug iteration count and fixes applied,<br>Final Status: PASS"]
    SaveReport --> Done(["validation-REPORT.md written —<br>proceed to Phase 5 Documentation"])

    Debug["Layer 4 — Debug cycle:<br>subagent_type='general-purpose'<br>Read failing file(s); identify root cause;<br>generate fix plan as XML with file, issue, action;<br>execute fix; re-run the failing layer"]
    Debug --> L1L2
```

---

## Phase 5 — Documentation

```mermaid
flowchart TD
    Start(["validation-REPORT.md written"]) --> Delegate["Delegate to plugin-docs-writer agent:<br>subagent_type='plugin-creator:plugin-docs-writer'<br>Context: ./plugins/{plugin-name} — all validated source files<br>Derive all content from source files only —<br>do not invent diagrams or examples"]

    Delegate --> Creates["Agent creates:<br>README.md (installation, usage, examples)<br>docs/skills.md if plugin has multiple skills<br>Configuration guide if hooks or MCP servers are present"]

    Creates --> Q{"Does agent output contain<br>'TODO: add example' in any section?"}
    Q -->|"Yes — example could not be derived from source"| Flag["Note the TODO locations —<br>request user provides example content<br>or confirm placeholder is acceptable"]
    Q -->|"No — all sections have derived content"| Done(["Documentation complete —<br>proceed to Phase 6 Final Verification"])
    Flag --> Done
```

---

## Phase 6 — Final Verification

```mermaid
flowchart TD
    Start(["Documentation complete"]) --> Check1{"Check 1 — Works Check:<br>Run: uvx skilllint@latest check ./plugins/{plugin-name}<br>Exit code = 0?"}

    Check1 -->|"Non-zero — validation failures remain"| Fix1["Return to Phase 4 —<br>re-run validation loop"]

    Check1 -->|"0 — validation passed"| Check2{"Check 2 — Quality Gates:<br>Does validation-REPORT.md Layer 3 section<br>show score >= 7 AND no critical issues listed?"}

    Check2 -->|"No — critical issues or score < 7"| Fix2["Return to Phase 4 —<br>re-run quality assessment"]

    Check2 -->|"Yes — quality threshold confirmed"| Check3{"Check 3 — Docs Check:<br>Does README.md exist at ./plugins/{plugin-name}/README.md<br>AND does it contain an installation section<br>AND at least one usage example?"}

    Check3 -->|"No — README missing or incomplete"| Fix3["Return to Phase 5 —<br>re-run documentation phase"]

    Check3 -->|"Yes — README present and complete"| Check4{"Check 4 — Honesty Check:<br>Does each factual claim in SKILL.md files<br>have a cited source (URL or reference path)<br>with an access date?"}

    Check4 -->|"No — uncited claims found"| Fix4["Delegate to ai-doc-optimizer:<br>subagent_type='plugin-creator:ai-doc-optimizer'<br>Add citations to all uncited factual claims"]
    Fix4 --> Check4
```

Routing by concern:
- Optimize existing content (improve clarity, fix structure, apply Anthropic prompt engineering principles) → `ai-doc-optimizer` agent (`plugin-creator:ai-doc-optimizer`)
- Audit quality (read-only, no writes, score against completeness categories) → `skill-auditor` agent (uses `/plugin-creator:audit-skill-completeness`)
- Sync content against upstream docs (add NEW/fix STALE from live sources) → `skill-content-updater` agent
- Write/rewrite description field only → `/plugin-creator:write-frontmatter-description` skill directly

```mermaid

    Check4 -->|"Yes — all claims cited"| Complete(["COMPLETE —<br>plugin validated, documented, and ready<br>for marketplace submission"])
```

---

## Agent Delegation Routing

```mermaid
flowchart TD
    Start(["Task to delegate"]) --> Q1{"User names a specific agent?"}

    Q1 -->|"Yes — explicit instruction"| Override["Use exactly the agent named —<br>explicit instruction overrides all routing"]

    Q1 -->|"No"| Q2{"Task type?"}

    Q2 -->|"Domain research, code pattern discovery,<br>architecture analysis, quality assessment"| Assessor["subagent_type='plugin-creator:plugin-assessor'"]

    Q2 -->|"Verbatim file retrieval — exact contents,<br>directory listings, keyword search<br>with NO interpretation required"| Explore["Explore agent (Haiku-based) —<br>retrieval ONLY;<br>never reasoning tasks"]

    Q2 -->|"Fetch and analyze official documentation<br>from external URLs"| GP["subagent_type='general-purpose'"]

    Q2 -->|"Schema and structure validation"| Scripts["Run validation scripts directly:<br>skilllint or create_plugin.py validate"]

    Q2 -->|"Documentation writing (README, guides)"| Docs["subagent_type='plugin-creator:plugin-docs-writer'"]

    Override --> Delegate(["Delegate with context —<br>name inputs, output file path, and expected format"])
    Assessor --> Delegate
    Explore --> Delegate
    GP --> Delegate
    Scripts --> Delegate
    Docs --> Delegate
```

---

## Failure Recovery Paths

```mermaid
flowchart TD
    F0(["Phase 0 BLOCKED"]) --> F0A["Identify which RT-ICA conditions<br>are marked MISSING"]
    F0A --> F0B["Request that specific information<br>from the user"]
    F0B --> F0C["Re-invoke rt-ica skill with<br>the now-available information"]
    F0C --> F0D{"All 6 conditions now<br>AVAILABLE or DERIVABLE?"}
    F0D -->|"No — still missing"| F0B
    F0D -->|"Yes"| F0E(["APPROVED — continue to Phase 0.5"])

    F2(["Phase 2 plan checker FAIL"]) --> F2A["Read the specific issues<br>the checker listed"]
    F2A --> F2B["Re-delegate to Plan agent<br>with checker feedback as additional input"]
    F2B --> F2C["Re-run plan checker on new plan"]
    F2C --> F2D{"Checker output: PASS or FAIL?"}
    F2D -->|"FAIL"| F2A
    F2D -->|"PASS"| F2E(["Proceed to 2c — save design-PLAN.md"])

    F4(["Phase 4 validation failure"]) --> F4A{"Which layer failed?"}
    F4A -->|"Layer 1 — script exit non-zero"| F4B["Read script output for error codes;<br>fix file(s) named in output"]
    F4A -->|"Layer 2 — schema violation with file:line"| F4C["Fix the exact field at the<br>file:line location reported"]
    F4A -->|"Layer 3 — quality score < 7<br>or critical issues listed"| F4D["Delegate fix to ai-doc-optimizer<br>(content optimization only) or general-purpose for structural issues"]
    F4B --> F4E["Re-run the failed layer only"]
    F4C --> F4E
    F4D --> F4E
    F4E --> F4F{"Layer now passes?"}
    F4F -->|"No"| F4A
    F4F -->|"Yes"| F4G(["Return to validation phase<br>from beginning to confirm all layers pass"])

    F6(["Phase 6 NOT COMPLETE"]) --> F6A{"Which check failed?"}
    F6A -->|"Check 1 — Works Check"| F6B(["Return to Phase 4"])
    F6A -->|"Check 2 — Quality Gates"| F6C(["Return to Phase 4"])
    F6A -->|"Check 3 — Docs Check"| F6D(["Return to Phase 5"])
    F6A -->|"Check 4 — Honesty Check"| F6E["Delegate citation additions<br>to ai-doc-optimizer;<br>re-run Check 4 when complete"]
```

Routing by concern:
- Optimize existing content (improve clarity, fix structure, apply Anthropic prompt engineering principles) → `ai-doc-optimizer` agent (`plugin-creator:ai-doc-optimizer`)
- Audit quality (read-only, no writes, score against completeness categories) → `skill-auditor` agent (uses `/plugin-creator:audit-skill-completeness`)
- Sync content against upstream docs (add NEW/fix STALE from live sources) → `skill-content-updater` agent
- Write/rewrite description field only → `/plugin-creator:write-frontmatter-description` skill directly

---

## Tool and Agent Reference

### Built-in Claude Code Agents

| Agent name | Model | Use for |
|---|---|---|
| `general-purpose` | inherits | Reasoning, analysis, implementation, debugging |
| `Explore` | haiku | Verbatim retrieval only — no reasoning tasks |
| `Plan` | inherits | Architecture planning, content structure decisions |

SOURCE: CLAUDE.md global instructions (accessed 2026-01-28)

### Plugin-Specific Agents

| Agent | subagent_type | Use for |
|---|---|---|
| `plugin-assessor` | `plugin-creator:plugin-assessor` | Domain research, code discovery, quality assessment |
| `plugin-docs-writer` | `plugin-creator:plugin-docs-writer` | README and documentation generation |
| `skill-auditor` | `plugin-creator:skill-auditor` | Read-only quality audit and completeness scoring |
| `skill-content-updater` | `plugin-creator:skill-content-updater` | Sync skill content against upstream sources |
| `ai-doc-optimizer` | `plugin-creator:ai-doc-optimizer` | Content optimization, citation addition, AI-facing docs |

SOURCE: Verified from plugin-creator agents directory

Routing by concern:
- Optimize existing content (improve clarity, fix structure, apply Anthropic prompt engineering principles) → `ai-doc-optimizer` agent (`plugin-creator:ai-doc-optimizer`)
- Audit quality (read-only, no writes, score against completeness categories) → `skill-auditor` agent (uses `/plugin-creator:audit-skill-completeness`)
- Sync content against upstream docs (add NEW/fix STALE from live sources) → `skill-content-updater` agent
- Write/rewrite description field only → `/plugin-creator:write-frontmatter-description` skill directly

### Validation Scripts

| Script | Command | Output |
|---|---|---|
| `skilllint` | `uvx skilllint@latest check {path}` | Exit code 0 = pass; non-zero = error codes with file:line |
| `create_plugin.py validate` | `uv run scripts/create_plugin.py validate {plugin-path}` | Pass/fail with structural issues |

SOURCE: Verified from plugin-creator scripts directory

### MCP Tools for Documentation

| Tool | Use for |
|---|---|
| `mcp__Ref__ref_read_url` | Fetch official docs by URL |
| `mcp__Ref__ref_search_documentation` | Search documentation by keyword |

SOURCE: Lines 9–12 of claude-plugins-reference-2026/SKILL.md

---

## Source

This workflow diagram documents the agentic plugin creation process defined in [SKILL.md](../SKILL.md).
Last updated: 2026-03-02
