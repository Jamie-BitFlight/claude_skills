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

The following diagram is the authoritative routing procedure. Eligible directory files: `**/SKILL.md`, `**/CLAUDE.md`, `**/AGENT.md`, `**/agents/*.md`, `**/rules/*.md`.

```mermaid
flowchart TD
    Start(["Path and arguments received"]) --> Exists{"Does path exist?"}
    Exists -->|"No"| Stop(["Report missing path and stop"])
    Exists -->|"Yes"| Mode{"Requested mode?"}
    Mode -->|"--analyze, --dry-run, or --report"| Analyze["Mode = ANALYZE; no process mutation"]
    Mode -->|"--represent"| Represent["Mode = REPRESENT; preserve process semantics"]
    Mode -->|"--improve or no mode"| Improve["Mode = IMPROVE; apply intent-preserving changes"]
    Analyze --> Scope{"Single file or directory?"}
    Represent --> Scope
    Improve --> Scope
    Scope -->|"Single file"| One["Run process-siren once with selected mode and target file"]
    Scope -->|"Directory"| Discover["Discover eligible files"]
    Discover --> PerFile["Run process-siren for each eligible file with selected mode"]
    PerFile --> Synthesize["Synthesize ProcessModels across material boundaries"]
    Synthesize --> Cross["Detect cross-file contract, invariant, assumption, ownership, and recovery gaps"]
    Cross --> Revalidate["Revalidate claims affected by cross-file findings or changes"]
    One --> Result["Return target result with evidence, status, blockers, and changes"]
    Revalidate --> Result
```

A blocked file does not stop unrelated files. Preserve its `BLOCKED_INTENT`, `UNVALIDATED`, or `INVALID` status and continue eligible independent work. In IMPROVE mode, do not finalize cross-file changes until synthesis and affected-claim revalidation complete.

