---
name: woo-sailor
description: Analyze, improve, or represent processes across a file or directory by delegating to process-siren. Uses the same semantic model and validation loop as single-process work; Mermaid is produced when it is the useful concise representation.
argument-hint: <file-or-directory> [--analyze|--improve|--represent] [--dry-run|--report]
user-invocable: true
context: fork
agent: process-siren:process-siren
---

You are about to process a set of files. Select --analyze, --improve, or --represent; default to --improve. --dry-run and --report imply read-only ANALYZE behavior.

<path>$0</path>
<options>$1</options>
<user_arguments>$ARGUMENTS</user_arguments>

If there is no <path> value, then stop, and say: /woo-sailor <file-or-directory> [--analyze|--improve|--represent] [--dry-run|--report]

The following diagram is the authoritative routing procedure. Eligible directory files: `**/SKILL.md`, `**/CLAUDE.md`, `**/AGENTS.md`, `**/AGENT.md`, `**/agents/*.md`, `**/rules/*.md`.

```mermaid
flowchart TD
    Start(["Path and arguments received"]) --> Exists{"Does path exist?"}
    Exists -->|"No"| Stop(["Report missing path and stop"])
    Exists -->|"Yes"| Mode{"Requested mode?"}
    Mode -->|"--analyze, --dry-run, or --report"| Analyze["Mode = ANALYZE; no mutation"]
    Mode -->|"--represent"| Represent["Mode = REPRESENT; preserve semantics"]
    Mode -->|"--improve or no mode"| Improve["Mode = IMPROVE"]
    Analyze --> Scope{"Single file or directory?"}
    Represent --> Scope
    Improve --> Scope
    Scope -->|"Single file"| One["Run process-siren with selected mode"]
    Scope -->|"Directory"| Discover["Discover eligible files; bind material source identities"]
    Discover --> Models["Run read-only ANALYZE for each file; collect ProcessModels and assessments"]
    Models --> Synthesize["Synthesize cross-file contracts, invariants, assumptions, ownership, and recovery"]
    Synthesize --> Route{"Selected mode?"}
    Route -->|"ANALYZE"| Aggregate["Return aggregate findings; preserve per-file assessments"]
    Route -->|"REPRESENT"| Render["Faithfully represent requested targets; retain authority and assessment limits"]
    Route -->|"IMPROVE"| Plan["Build one cross-file candidate; validate dependencies and affected claims"]
    Plan --> Safe{"Contract, evidence and conditional-apply requirements satisfied?"}
    Safe -->|"No"| Block["Do not apply dependent set; preserve proposal and named blockers"]
    Safe -->|"Yes"| Apply["Apply through material-change lifecycle; verify resulting state"]
    One --> Result["Return caller envelope plus assessments, evidence, changes and remaining work"]
    Aggregate --> Result
    Render --> Result
    Block --> Result
    Apply --> Result
```

A blocked file does not stop unrelated independent work. `UNVALIDATED` or `INVALID` does not by itself block ANALYZE or faithful REPRESENT. In IMPROVE, block only the dependent mutation set whose required contract, evidence, intent, or apply guarantee is unresolved; never write per-file improvements before cross-file synthesis establishes a coherent apply set.

Before material or concurrent writes, follow [material-change-lifecycle.md](../improve-processes/references/material-change-lifecycle.md), including source/dependency rechecks and safe multi-file publication. A repeated/no-progress candidate or partial application remains explicit, not a completed coherent improvement. Preserve the caller's exact task-status envelope separately from per-target assessments; successfully finishing analysis does not change INVALID into READY.
