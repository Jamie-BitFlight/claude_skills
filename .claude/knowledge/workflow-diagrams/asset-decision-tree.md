# Asset Category Decision Tree

Guide for selecting the right extension type: Skill vs Command vs Agent vs Hook.

---

## Quick Decision Flow

```mermaid
flowchart TD
    START["Need to extend<br/>Claude's capabilities?"]

    Q1{"Does it need to<br/>run automatically<br/>on events?"}
    Q2{"Is it user-invocable<br/>with /command?"}
    Q3{"Does it require<br/>autonomous execution<br/>in separate context?"}
    Q4{"Is it knowledge,<br/>patterns, or<br/>instructions?"}

    HOOK["→ HOOK<br/>Event-triggered automation"]
    COMMAND["→ COMMAND<br/>User-invocable action"]
    AGENT["→ AGENT<br/>Autonomous specialist"]
    SKILL["→ SKILL<br/>Loadable knowledge"]

    START --> Q1
    Q1 -->|"Yes"| HOOK
    Q1 -->|"No"| Q2
    Q2 -->|"Yes"| COMMAND
    Q2 -->|"No"| Q3
    Q3 -->|"Yes"| AGENT
    Q3 -->|"No"| Q4
    Q4 -->|"Yes"| SKILL
    Q4 -->|"No"| START
```

---

## Detailed Decision Matrix

```mermaid
flowchart TB
    subgraph CRITERIA["Selection Criteria"]
        direction LR
        C1["Invocation Method"]
        C2["Execution Context"]
        C3["Autonomy Level"]
        C4["Persistence"]
    end

    subgraph SKILL_BOX["SKILL"]
        S1["Loaded on demand<br/>or by other assets"]
        S2["Runs in current<br/>context window"]
        S3["Provides guidance,<br/>not autonomous action"]
        S4["Persists as knowledge<br/>for session duration"]
    end

    subgraph COMMAND_BOX["COMMAND"]
        CMD1["User types /name<br/>or model invokes"]
        CMD2["Runs in current<br/>context window"]
        CMD3["Executes defined<br/>action sequence"]
        CMD4["One-time execution,<br/>may modify state"]
    end

    subgraph AGENT_BOX["AGENT"]
        A1["Delegated via<br/>Agent tool"]
        A2["Runs in separate<br/>context window"]
        A3["Fully autonomous<br/>within scope"]
        A4["Returns results,<br/>signals DONE/BLOCKED"]
    end

    subgraph HOOK_BOX["HOOK"]
        H1["Triggered by<br/>system events"]
        H2["Runs in shell<br/>or Node.js"]
        H3["Automated,<br/>no human trigger"]
        H4["Executes on<br/>every event match"]
    end

    C1 --> S1 & CMD1 & A1 & H1
    C2 --> S2 & CMD2 & A2 & H2
    C3 --> S3 & CMD3 & A3 & H3
    C4 --> S4 & CMD4 & A4 & H4
```

---

## Use Case Decision Trees

### When to Use a SKILL

```mermaid
flowchart TD
    Q1{"Reusable knowledge<br/>or patterns?"}
    Q2{"Reference material<br/>for multiple tasks?"}
    Q3{"Workflow guidance<br/>or methodology?"}
    Q4{"Tool-specific<br/>expertise?"}

    YES["✅ Create a SKILL"]
    NO["❌ Not a skill"]

    Q1 -->|"Yes"| YES
    Q1 -->|"No"| Q2
    Q2 -->|"Yes"| YES
    Q2 -->|"No"| Q3
    Q3 -->|"Yes"| YES
    Q3 -->|"No"| Q4
    Q4 -->|"Yes"| YES
    Q4 -->|"No"| NO

    subgraph EXAMPLES["Skill Examples"]
        E1["rt-ica → Requirements methodology"]
        E2["scientific-method:scientific-thinking → Investigation pattern"]
        E3["verify → Completion checklist"]
        E4["delegate → Delegation template"]
    end

    YES --> EXAMPLES
```

**Skill Characteristics:**

- Loadable via `Skill(skill: "name")` or `@skillname`
- Contains SKILL.md with frontmatter and instructions
- Can include reference files for additional context
- No autonomous execution - provides guidance only

---

### When to Use a COMMAND

```mermaid
flowchart TD
    Q1{"User explicitly<br/>triggers action?"}
    Q2{"Single discrete<br/>operation?"}
    Q3{"Needs argument<br/>parsing?"}
    Q4{"Should appear in<br/>/help listing?"}

    YES["✅ Create a COMMAND"]
    NO["❌ Not a command"]

    Q1 -->|"Yes"| Q2
    Q1 -->|"No"| NO
    Q2 -->|"Yes"| Q3
    Q2 -->|"No"| NO
    Q3 -->|"Any"| Q4
    Q4 -->|"Yes"| YES
    Q4 -->|"No"| NO

    subgraph EXAMPLES["Command Examples"]
        E1["/am-i-complete → Check completion"]
        E2["/think → Step-back reasoning"]
        E3["/sessions → Session management"]
        E4["/agent-orchestration:delegate → Decompose, dispatch, adjudicate"]
    end

    YES --> EXAMPLES
```

**Command Characteristics:**

- Invoked with `/commandname` or `/commandname args`
- Lives in `.claude/commands/` directory
- Markdown file with frontmatter
- Executes in orchestrator's context
- Can fork context if `context_fork: true`

---

### When to Use an AGENT

```mermaid
flowchart TD
    Q1{"Requires autonomous<br/>decision-making?"}
    Q2{"Needs separate<br/>context window?"}
    Q3{"Specialist expertise<br/>for specific domain?"}
    Q4{"Should signal<br/>DONE/BLOCKED?"}

    YES["✅ Create an AGENT"]
    NO["❌ Not an agent"]

    Q1 -->|"Yes"| Q2
    Q1 -->|"No"| NO
    Q2 -->|"Yes"| Q3
    Q2 -->|"No"| NO
    Q3 -->|"Yes"| Q4
    Q3 -->|"No"| NO
    Q4 -->|"Yes"| YES
    Q4 -->|"No"| NO

    subgraph EXAMPLES["Agent Examples"]
        E1["context-gathering → Research specialist"]
        E2["code-review → Quality specialist"]
        E3["plugin-assessor → Validation specialist"]
        E4["skill-refactorer → Refactoring specialist"]
    end

    YES --> EXAMPLES
```

**Agent Characteristics:**

- Delegated via `Agent(subagent_type="name", prompt="...")`
- Lives in `.claude/agents/` directory
- YAML frontmatter with model, tools, allowed_tools
- Runs in isolated context window
- Returns results to orchestrator

---

### When to Use a HOOK

```mermaid
flowchart TD
    Q1{"Triggered by<br/>system event?"}
    Q2{"No human<br/>intervention needed?"}
    Q3{"Same action<br/>every time?"}
    Q4{"Shell or Node.js<br/>execution?"}

    YES["✅ Create a HOOK"]
    NO["❌ Not a hook"]

    Q1 -->|"Yes"| Q2
    Q1 -->|"No"| NO
    Q2 -->|"Yes"| Q3
    Q2 -->|"No"| NO
    Q3 -->|"Yes"| Q4
    Q3 -->|"No"| NO
    Q4 -->|"Yes"| YES
    Q4 -->|"No"| NO

    subgraph EXAMPLES["Hook Examples"]
        E1["session-start-rtica.cjs → Auto-load rt-ica"]
        E2["pre-commit → Validate before commit"]
        E3["post-tool → Log tool usage"]
    end

    YES --> EXAMPLES
```

**Hook Characteristics:**

- Defined in `settings.json` hooks array
- Triggered by events: session-start, pre-tool, post-tool, etc.
- Runs shell command or Node.js script
- Cannot prompt user - automated only
- Exit codes control flow (0=continue, non-0=block)

---

## Comparison Table

| Aspect            | Skill              | Command          | Agent             | Hook             |
| ----------------- | ------------------ | ---------------- | ----------------- | ---------------- |
| **Invocation**    | Load via Skill()   | User types /name | Agent() delegation | System event     |
| **Context**       | Orchestrator's     | Orchestrator's   | Separate window   | Shell/Node       |
| **Autonomy**      | Guidance only      | Execute action   | Fully autonomous  | Automated        |
| **File Location** | skills/\*/SKILL.md | commands/\*.md   | agents/\*.md      | settings.json    |
| **User Visible**  | @mention           | /help listing    | Agent output       | Silent           |
| **Arguments**     | N/A                | $ARGUMENTS       | prompt parameter  | Environment vars |
| **Return Value**  | Knowledge loaded   | Action complete  | DONE/BLOCKED      | Exit code        |

---

## Decision Flowchart Summary

```text
START: What capability do I need?
│
├─► Runs on system events automatically?
│   └─► YES → HOOK
│
├─► User explicitly invokes with slash?
│   └─► YES → COMMAND
│
├─► Needs separate context, autonomous work?
│   └─► YES → AGENT
│
└─► Knowledge, patterns, or guidance?
    └─► YES → SKILL
```

---

## Common Mistakes

| Mistake                          | Problem                     | Correct Approach               |
| -------------------------------- | --------------------------- | ------------------------------ |
| Creating agent for simple lookup | Wastes context window       | Use skill with reference files |
| Creating skill for user action   | Skills can't take action    | Use command for actions        |
| Creating command for automation  | Commands need user trigger  | Use hook for automation        |
| Creating hook for guidance       | Hooks can't provide context | Use skill for guidance         |

---

## Combination Patterns

Assets often work together:

```mermaid
flowchart LR
    HOOK["Hook<br/>Auto-triggers on event"]
    SKILL["Skill<br/>Loads knowledge"]
    COMMAND["Command<br/>User invokes action"]
    AGENT["Agent<br/>Executes autonomously"]

    HOOK -->|"Loads"| SKILL
    COMMAND -->|"Uses guidance from"| SKILL
    COMMAND -->|"Delegates to"| AGENT
    AGENT -->|"Follows patterns in"| SKILL
```

**Example: session-start-rtica.cjs**

1. Hook triggers on session start
2. Loads rt-ica skill
3. Skill provides requirements assessment methodology
4. User can also invoke via /rt-ica command

---

## Navigation

- **Previous:** [Master Workflow](./master-workflow.md)
- **Next:** [Simple Task Workflow](./simple-task-workflow.md)
- **Back to:** [Index](./README.md)
