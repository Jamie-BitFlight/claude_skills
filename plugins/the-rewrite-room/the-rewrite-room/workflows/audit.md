# Audit Workflow

Loaded by: `/rwr:audit` command
Orchestrator: Claude (reads this workflow and executes steps)

## Step 1 — Classify Task

Determine task type from $ARGUMENTS:

```mermaid
flowchart TD
    Start([$ARGUMENTS]) --> Q{Signal words?}
    Q -->|"drift, out of date, stale docs, undocumented, documented but, doesn't match code, audit"| Drift[Task type: drift-audit]
    Q -->|"sync, update docs, docs behind, after refactor, after implementing"| Sync[Task type: documentation-sync]
    Q -->|"freshness, stale headers, governance, track changes, last updated"| Fresh[Task type: freshness]
    Q -->|Ambiguous| Ask[Ask user — see disambiguation below]
```

Disambiguation prompt when ambiguous:

> "Is this (a) checking if docs match code, (b) updating docs after code changed, or (c) tracking doc freshness?"

## Step 2 — Read Agent Protocol

Before spawning, read the target agent's file to understand its exact required inputs and output format:

- drift-audit: Read `plugins/development-harness/agents/doc-drift-auditor.md`
- documentation-sync: Read `plugins/development-harness/agents/service-docs-maintainer.md`
- freshness: Read `~/.claude/agents/doc-freshness-guardian.md` (doc-freshness-guardian is a personal agent, not bundled with this plugin)

## Step 3 — Spawn Agent

Construct prompt using exact input format the agent expects (from Step 2 read).

For drift-audit:

```text
Agent(
  subagent_type="development-harness:doc-drift-auditor",
  prompt="<task description>

Scope: <file paths or directories>
Project root: <path>"
)
```

For documentation-sync:

```text
Agent(
  subagent_type="development-harness:service-docs-maintainer",
  prompt="<description of what code changed>

Affected files: <list>"
)
```

Note: service-docs-maintainer does NOT write a summary file — its output is response text only.

For freshness:

```text
Agent(
  subagent_type="doc-freshness-guardian",
  prompt="<task description>

Files to check: <list>"
)
```

## Step 4 — Handle Return

```mermaid
flowchart TD
    Return([Agent returns]) --> Q{Agent type?}
    Q -->|drift-audit STATUS: DONE| Report[Report findings to user]
    Report --> Chain{Markdown files modified?}
    Chain -->|Yes| Validate[Run normalize_frontmatter.py on modified files\nuv run plugins/plugin-creator/scripts/normalize_frontmatter.py &lt;file&gt;]
    Chain -->|No| Done([Done])
    Q -->|drift-audit STATUS: BLOCKED| ShowNeeded[Show NEEDED list to user]
    ShowNeeded --> Ask[Ask user to provide missing inputs]
    Ask --> Retry[Return to Step 3 with complete inputs]
    Q -->|documentation-sync completes| ShowSummary[Show summary of docs changed]
    ShowSummary --> Offer["Offer: Run drift audit to verify docs now match code? (y/n)"]
    Q -->|freshness returns| ShowFreshness[Show freshness report]
    ShowFreshness --> Highlight[Highlight red greater than 90d stale items first]
```

## Output Contract

Audit workflow VALIDATION subfields:

```text
VALIDATION:
  - citation-check: PASS|FAIL  (drift-audit only — all findings have file:line evidence)
  - link-check: PASS|FAIL      (if markdown files modified)
```
