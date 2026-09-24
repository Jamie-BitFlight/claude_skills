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

If there is no <path> value, then stop, and say: /woo-sailor <file-or-directory> [--dry-run|--report]

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
    Scope -->|"Directory"| Discover["Discover eligible files"]
    Discover --> Models["Run read-only ANALYZE for each file; collect ProcessModels and statuses"]
    Models --> Synthesize["Synthesize cross-file contracts, invariants, assumptions, ownership, and recovery"]
    Synthesize --> Route{"Selected mode?"}
    Route -->|"ANALYZE"| Aggregate["Return aggregate findings; preserve per-file statuses"]
    Route -->|"REPRESENT"| Render["Run faithful REPRESENT for requested targets; INVALID/UNVALIDATED may still be represented with status"]
    Route -->|"IMPROVE"| Plan["Build one cross-file change set; validate dependencies and affected claims before writes"]
    Plan --> Safe{"Any dependency or intent blocker prevents coherent apply?"}
    Safe -->|"Yes"| Block["Do not apply dependent change set; report BLOCKED_INTENT/INVALID/UNVALIDATED evidence as applicable"]
    Safe -->|"No"| Apply["Apply validated change set, then revalidate affected claims/interfaces"]
    One --> Result["Return target result with evidence, status, blockers, and changes"]
    Aggregate --> Result
    Render --> Result
    Block --> Result
    Apply --> Result
```

A blocked file does not stop unrelated independent work. `UNVALIDATED` or `INVALID` does not by itself block ANALYZE or faithful REPRESENT. In IMPROVE, block only the dependent mutation set whose required contract, evidence, or intent is unresolved; never write per-file improvements before cross-file synthesis establishes a coherent apply set.
