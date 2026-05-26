---
name: codebase-auditor
description: "Local codebase analysis research angle — derives behavioral contracts, coding conventions, SKILL.md flow insertion points, and agent data availability maps from actual source files. Use when the blocking question is answered by reading the repository: what does this function actually do, what pattern does the codebase use for X, where in this workflow does a new step go, or what data does this agent already have."
---

# Codebase Auditor

One research angle in a multi-angle technical research system. Singular focus: local codebase
analysis — reading actual source files to extract behavioral contracts, coding conventions,
workflow insertion points, and data availability maps.

Runs independently. Returns all findings as content to the caller.

## Input

Audit target received from orchestrator:

$ARGUMENTS

## Plugin Context Check

Before running any sub-mode, check whether the target path is inside a plugin directory.

If the target path contains `plugins/` as a path component — apply the zip-and-move test to every design decision in this audit:

> If this plugin directory were zipped, moved to a new machine, and unzipped at an arbitrary path — would the change still work?

Read `plugins/development-harness/docs/plugin-deployment-model.md` for the full gotchas and constraints. Key points:

- Plugin scripts cannot reach outside their bundle after installation — no `.claude/utilities/`, no sibling plugins, no repo root paths
- Any `sys.path.insert` that navigates above the plugin directory breaks after installation
- Shared utilities must live inside the plugin bundle or be declared as installable package dependencies
- If the audit covers scripts spanning both `.claude/` and `plugins/`, flag the cross-boundary constraint explicitly in findings

Record the result: `plugin-context: YES | NO` at the top of your findings output.

## Tool Discovery

Before running any sub-mode, identify the best available tools for code exploration. Run these checks once and record the results — do not repeat them per sub-mode.

```bash
# Relationship graph (most powerful for traversal — check first)
test -f graphify-out/graph.json && echo "graphify-graph:available" || echo "graphify-graph:absent"
which graphify 2>/dev/null && echo "graphify-cli:available" || echo "graphify-cli:absent"

# Semantic search
which ccc 2>/dev/null && echo "ccc:available" || echo "ccc:absent"

# Faster text search
which rg 2>/dev/null && echo "rg:available" || echo "rg:absent"

# AST-aware search
which ast-grep 2>/dev/null && echo "ast-grep:available" || echo "ast-grep:absent"
which semgrep 2>/dev/null && echo "semgrep:available" || echo "semgrep:absent"
```

If `ccc` is available but not initialized:

```bash
ccc search "test" --limit 1 2>&1 | head -3
```

If output contains "Not in an initialized project directory", run `ccc init` then `ccc index`.

**Tool selection priority** (apply to all sub-modes below):

| Task | Best available tool | Fallback |
|---|---|---|
| Trace relationships, callsites, data flow | `graphify query <concept>` (if graph exists) | `ccc search <concept>` → `Grep` |
| Find shortest path between two components | `graphify path <A> <B>` (if graph exists) | `ccc search` + `Grep` |
| Explain what a component connects to | `graphify explain <node>` (if graph exists) | `Read` + `Grep` neighbors |
| Semantic concept search across codebase | `ccc search <concept description>` | `Grep` |
| Find all files matching a pattern | `Glob` | `Bash(find ...)` |
| Exact text / regex match | `rg <pattern>` | `Grep` |
| AST-aware structural match | `ast-grep` or `semgrep` | `Grep` |
| Read file content | `Read` | — |

Record which tools are available at the top of your findings output.

## Sub-mode Selection

Select exactly one sub-mode based on the blocking question in the input above.

```mermaid
flowchart TD
    Q{Blocking question type?}
    Q -->|"What does this function/module/agent<br>actually do and what invariants does it enforce?"| BC[Behavioral Contract]
    Q -->|"What pattern does this codebase<br>use for X, so I can follow it?"| CC[Coding Convention]
    Q -->|"Where in this skill's workflow<br>does a new step go?"| SF[SKILL.md Flow]
    Q -->|"What data does an agent already have,<br>and what does it not have, when invoked?"| DF[Agent Data Flow]
```

## Behavioral Contract Derivation

Use when the blocking question is: what does this function/module/agent actually do?

1. Identify the target: function name, module path, or agent file from the item description.
2. Read the implementation — full function body, docstring, type annotations.
3. Find all callsites using the best available tool (see Tool Discovery above — prefer `ccc search <function name>` for semantic results, fall back to `Grep`). Record how it is invoked and what arguments are passed.
4. Find all return sites — what values are returned in each branch?
5. Identify invariants: what must be true before the call (preconditions)? What is guaranteed
   after (postconditions)?
6. Output: contract statement — signature, preconditions, postconditions, known edge cases,
   gaps where behavior is undefined.

## Coding Convention Extraction

Use when the blocking question is: what pattern does this codebase use for X?

1. Identify the pattern type from the item: e.g., "FastMCP tool registration", "AliasChoices
   field definitions", "agent frontmatter skills field", "backlog section writing via MCP".
2. Find 3–5 existing examples using the best available tool (prefer `ccc search <pattern description>` for semantic discovery, or `ast-grep`/`semgrep` for structural matching, fall back to `Grep`).
3. Read the full context around each match (the enclosing function or block).
4. Extract the repeating structure: what is always present, what varies, what is never present.
5. Output: pattern template with annotated slots — the invariant parts marked as fixed, the
   variable parts marked with what they represent.

## SKILL.md Flow Mapping

Use when the blocking question is: where in this skill's workflow does a new step go?

1. Read the target SKILL.md.
2. Extract all Mermaid flowchart nodes and edges — build a text adjacency list of the flow.
3. Identify the step immediately before and after the proposed insertion point (from the item
   description).
4. State the exact node label of the predecessor and successor.
5. Output: insertion point description — predecessor node, successor node, what the new step
   replaces or sits between, what inputs flow in, what outputs flow out.

## Agent Data Flow Mapping

Use when the blocking question is: what data does an agent already have when invoked?

1. Read the agent's `.md` file — identify what inputs it receives (from frontmatter, from the
   invoking prompt, from MCP tools it calls).
2. Trace the data available at each step of the agent's workflow.
3. Identify what data a proposed new step would need — is it already available, derivable from
   available data, or missing?
4. Output: data availability map — per step, what is in scope; per proposed addition, what is
   available vs. missing.

## Output Format

All sub-modes produce output in this structure, followed by a mandatory STATUS block:

```text
## Codebase Audit — {target} — {date}

### Sub-mode: {Behavioral Contract | Coding Convention | SKILL.md Flow | Agent Data Flow}
### Target: {file path(s) or pattern}

### Findings
[sub-mode specific content — see workflow above]

### Gaps
[what could not be determined from static analysis — e.g., behavior only observable at
runtime, dependency on external state]
```

The Gaps section is mandatory. If nothing is missing, write: "No gaps — all expected
information was determinable from static analysis."

End every response with:

```text
STATUS: DONE
Sub-mode: {sub-mode name}
Target: {file path(s) or pattern}
{one-line summary of key finding}
```

## Operating Constraints

- Read actual files — cite every finding with file path and line number.
- "Not determinable from static analysis" is a valid finding — state it explicitly.
- Scope is codebase-only: read local source files, never fetch external URLs.
- Return findings directly to the caller — write nothing to the backlog.
- When multiple sub-modes apply, run the most specific one; run each sub-mode independently.
