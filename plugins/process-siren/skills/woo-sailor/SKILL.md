---
name: woo-sailor
description: Analyze, improve, or represent processes across a file or directory by delegating to process-siren. Uses the same semantic model and validation loop as single-process work; Mermaid is produced when it is the useful concise representation.
argument-hint: <file-or-directory> [--analyze|--improve|--represent] [--dry-run|--report]
user-invocable: true
context: fork
agent: process-siren:process-siren
---

You are about to process a set of files. Read every flag in <user_arguments>. Select --analyze, --improve, or --represent; default to --improve. --analyze, --dry-run or --report anywhere in the arguments selects read-only ANALYZE, whatever other mode flag is present.

<path>$0</path>
<user_arguments>$ARGUMENTS</user_arguments>

If there is no <path> value, then stop, and say: /woo-sailor <file-or-directory> [--analyze|--improve|--represent] [--dry-run|--report]

Before reading or analyzing the target, load `/process-siren:improve-processes` and use its semantic model, validation loop, Recursion Safety, and Result Contract. Execute the selected mode in the current invocation context. A host-applied context fork or agent route is optional acceleration, not a precondition for this workflow.

The following diagram is the authoritative routing procedure. Eligible directory files: `**/SKILL.md`, `**/CLAUDE.md`, `**/AGENTS.md`, `**/AGENT.md`, `**/agents/*.md`, `**/rules/*.md`.

```mermaid
flowchart TD
    Start(["Path and arguments received"]) --> Exists{"Does path exist?"}
    Exists -->|"No"| Stop(["Report missing path and stop"])
    Exists -->|"Yes"| ReadOnly{"Any of --analyze, --dry-run, --report<br>in user_arguments?"}
    ReadOnly -->|"Yes"| Analyze["Mode = ANALYZE; no mutation"]
    ReadOnly -->|"No"| Mode{"Mode flags in user_arguments?"}
    Mode -->|"--improve and --represent"| Conflict(["Report conflicting mode flags and stop"])
    Mode -->|"--represent"| Represent["Mode = REPRESENT; preserve semantics"]
    Mode -->|"--improve or none"| Improve["Mode = IMPROVE"]
    Analyze --> Scope{"Single file or directory?"}
    Represent --> Scope
    Improve --> Scope
    Scope -->|"Single file"| One["Execute selected mode in the current invocation context"]
    Scope -->|"Directory"| Discover["Discover eligible files; bind material source identities"]
    Discover --> Models["Analyze each file read-only in the current invocation context; collect ProcessModels and assessments"]
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

For the requested scope, execute `/process-siren:improve-processes` directly after loading it; keep all same-scope work in this invocation. When analysis requires a strictly narrower subsystem, boundary, claim, or unresolved dependency, descend according to its Recursion Safety procedure.

When the selected mode is REPRESENT, load `/process-siren:mermaids-treasure` and render the faithful Mermaid projection. In ANALYZE or IMPROVE, load it and render Mermaid only when that would materially improve the requested result; otherwise return the process model and findings without Mermaid.

A blocked file does not stop unrelated independent work. `UNVALIDATED` or `INVALID` does not by itself block ANALYZE or faithful REPRESENT. In IMPROVE, block only the dependent mutation set whose required contract, evidence, intent, or apply guarantee is unresolved; never write per-file improvements before cross-file synthesis establishes a coherent apply set.

Before material or concurrent writes, load the material-change lifecycle reference that `/process-siren:improve-processes` links under Evidence-Driven Improvement; it defines source/dependency rechecks, conditional apply and safe multi-file publication. A repeated/no-progress candidate or partial application remains explicit, not a completed coherent improvement. Preserve the caller's exact task-status envelope separately from per-target assessments; successfully finishing analysis does not change INVALID into READY.
