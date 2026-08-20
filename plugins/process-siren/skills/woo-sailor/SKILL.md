---
name: woo-sailor
description: Optimize processes in a file or directory by converting prose/bullet workflows to Mermaid diagrams — delegates to the process-siren:process-siren agent. Use when given a single SKILL.md, agent file, CLAUDE.md, or rules file to convert, or a directory containing any of those. Supports --dry-run or --report for read-only planning mode.
argument-hint: <file-or-directory> [--dry-run|--report]
user-invocable: true
context: fork
agent: process-siren:process-siren
---

You are about to optimize a set of files.

<path>$0</path>
<options>$1</options>
<user_arguments>$ARGUMENTS</user_arguments>

If there is no <path> value, then stop, and say: /woo-sailor <file-or-directory> [--dry-run|--report]

The following diagram is the authoritative procedure for argument handling and execution routing. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

Eligible file patterns for directory mode: `**/SKILL.md`, `**/CLAUDE.md`, `**/AGENT.md`, `**/agents/*.md`, `**/rules/*.md`. For a single file, Read it to understand why the user wanted optimizations applied — it may contain inline documentation, embedded AI prompts, or a process image.

```mermaid
flowchart TD
    Start(["Path available"]) --> Q1{"Glob pattern '<path>{/*,*}'<br>— any results?"}
    Q1 -->|"No results — path does not exist"| Stop(["Output exactly: 'A file or directory to process must be provided.'<br>Stop."])
    Q1 -->|"One result equal to <path> — single file"| Q2File{"Is DRY_RUN true?"}
    Q1 -->|"Results are children of <path> — directory"| Q2Dir{"Is DRY_RUN true?"}
    Q2File -->|"Yes"| DryFile["Spawn Agent(subagent_type='process-siren:process-siren',<br>prompt='Read-only mode. Report every section you would<br>optimize and how. Make NO edits. Target file: <path>')"]
    Q2File -->|"No"| LiveFile["Spawn Agent(subagent_type='process-siren:process-siren',<br>prompt='Optimize all processes in this file in-place.<br>Target file: <path>')"]
    Q2Dir -->|"Yes"| DryFilter["Glob <path> using eligible patterns:<br>SKILL.md, CLAUDE.md, AGENT.md, agents/*.md, rules/*.md"]
    Q2Dir -->|"No"| LiveFilter["Glob <path> using eligible patterns:<br>SKILL.md, CLAUDE.md, AGENT.md, agents/*.md, rules/*.md"]
    DryFilter --> DryDir["For each eligible file:<br>Spawn Agent(subagent_type='process-siren:process-siren',<br>prompt='Read-only mode. Report every section you would<br>optimize and how. Make NO edits. Target file: {file path}')"]
    LiveFilter --> LiveDir["For each eligible file:<br>Spawn Agent(subagent_type='process-siren:process-siren',<br>prompt='Optimize all processes in this file in-place.<br>Target file: {file path}')"]
    DryFile --> QBlockedFile{"Agent returned BLOCKED?"}
    LiveFile --> QBlockedFile
    DryDir --> QBlockedDir{"Any agent returned BLOCKED?"}
    LiveDir --> QBlockedDir
    QBlockedFile -->|"Yes"| RelayFile["Surface blocking message and file path to user. Stop."]
    QBlockedFile -->|"No"| Report(["Return report"])
    QBlockedDir -->|"Yes — per blocked file"| RelayDir["Surface blocking message and file path to user.<br>Skip that file; continue others."]
    QBlockedDir -->|"No"| Done(["All eligible files processed"])
    RelayDir --> Done
```
