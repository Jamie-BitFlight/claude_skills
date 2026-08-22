# Ecosystem Context Patterns

Detailed analysis of ECOSYSTEM CONTEXT anti-patterns and correct patterns for delegating to sub-agents.

## The Inheritance Rule

Sub-agents automatically inherit the following context. Do not repeat any of it in ECOSYSTEM CONTEXT:

- Both CLAUDE.md files (global `~/.claude/CLAUDE.md` + project `.claude/CLAUDE.md`)
- Rules files (e.g., `source-fidelity.md`)
- MEMORY.md content
- Git status snapshot
- Environment info (platform, shell, working directory)
- Current date
- All tool descriptions (including tool usage guidelines, git safety rules, PR workflow)
- Deferred MCP tool list (via ToolSearch)

Anything in these sources is already visible to the agent. Repeating it wastes prompt tokens and trains the orchestrator to parrot instead of provide unique value.

---

## Anti-Pattern 1: Tool List Enumeration

**Why this anti-pattern is harmful:**

The tool-list anti-pattern comes from slot-filling behavior triggered by the word "RESOURCES." When the orchestrator sees a list-style heading during generation, it fills the slot with the most readily available pattern from training data — tool names.

**Anti-pattern example (reductive, limiting):**

<eg>
AVAILABLE RESOURCES:
- WebFetch tool
- Read tool
- Bash tool
</eg>

**Problems with this pattern:**

1. Lists specific tools implying these are the only options available
2. Listing `WebFetch` without mentioning superior MCP alternatives causes agents to use low-fidelity tools
3. Provides no context about the project ecosystem or toolchain
4. Agents cannot make informed tool selection decisions from a tool list alone
5. Omits authenticated CLIs, MCP specialists, activated skills, and domain conventions

**Why tool lists feel natural but are wrong:**

The orchestrator has 50+ tools available, including specialized MCP servers for documentation, web research, GitHub, Docker, and more. A list of 3 generic tools implies the rest do not exist or should not be used.

---

## Anti-Pattern 2: Parroting Inherited Context

This is the more subtle and dangerous anti-pattern. The orchestrator repeats information that agents already receive through context inheritance.

**Parroting anti-pattern example:**

<eg>
ECOSYSTEM CONTEXT:
- Full project context available — explore freely with all tools
- Check <functions> list for MCP tools — prefer MCP specialists (Ref, context7, exa) over built-in alternatives
- Check <available_skills> and activate relevant skills for domain expertise
- Maximize parallel execution for independent tool calls
- This Python project uses `uv` — use `uv run python` instead of `python3`
</eg>

**Why each line is redundant:**

- "Full project context available" — agents always have full tool access; this is the default state
- "Check `<functions>` list for MCP tools" — tool descriptions already explain this to agents
- "Check `<available_skills>` and activate relevant skills" — CLAUDE.md already instructs skill activation
- "Maximize parallel execution" — CLAUDE.md already instructs this explicitly
- "This Python project uses `uv`" — project CLAUDE.md already documents the toolchain

This pattern trains the orchestrator to treat ECOSYSTEM CONTEXT as a boilerplate section to fill rather than as a place for genuinely unique context. It also wastes token budget that could hold real observations.

---

## Correct Pattern: Session-Specific Facts Only

**What belongs in ECOSYSTEM CONTEXT:**

Information that exists nowhere the agent can see — session-specific or task-specific facts that vary per run.

**Correct pattern example:**

<eg>
ECOSYSTEM CONTEXT:
- The `gh` CLI is pre-authenticated for GitHub operations (issues, PRs, API queries)
- CI logs for PR #42 accessible via MCP GitHub tool
- Recent linting reports in `.tmp/reports/` show previously resolved issues
</eg>

**Why this works:**

1. Authentication state — whether a CLI is authenticated varies per session; agents cannot assume it from CLAUDE.md
2. Task-specific access — CI logs for a specific PR are not in any static file
3. Non-obvious discovery shortcuts — file locations that would require extra exploration to find

---

## Pattern Components

### Authenticated CLI Tools

When CLI tools are pre-authenticated, explicitly state this — authentication state is session-specific:

<eg>
The `gh` CLI is pre-authenticated for GitHub operations
The `glab` CLI is configured for GitLab access
AWS CLI is configured with credentials for the staging account
</eg>

**Why**: CLAUDE.md may document that `gh` is available, but it cannot know whether it is authenticated in the current session. This is genuinely new information.

### Session-Specific Access

State task-relevant resources that are specific to this delegation:

<eg>
CI logs for PR #42 accessible via MCP GitHub tool
The staging deployment at staging.example.com is available for testing
Database seed data is loaded at localhost:5432
</eg>

**Why**: These facts vary per task and session. They are not discoverable from project files.

### Non-Obvious Document Locations

Point to locations that would require extra exploration to discover organically:

<eg>
Recent linting reports in `.tmp/reports/` document previously resolved issues
Package validation scripts in `./scripts/` — see README.md for usage
Architecture decision records in `./docs/adr/`
</eg>

**Why**: These locations may not be obvious from the directory structure. A hint saves investigation time. Do not list obvious locations (tests/, src/, etc.) that any agent would check first.

### MCP Tool Preferences for This Task

When a specific MCP tool is particularly relevant to the task at hand, name it:

<eg>
Use `mcp-server-docker` for container operations — it has direct daemon access
CI logs accessible via MCP GitHub tool (faster than `gh run view` for log content)
</eg>

Do not name MCP tools generically ("MCP servers installed — check your functions list") — that is already in the tool descriptions. Name specific tools only when they are the best fit for a specific task.

**Documentation fidelity hierarchy** (for reference when recommending documentation tools):

- `Ref` — high fidelity (output IS the source, verbatim)
- `exa` — medium fidelity (Markdown-formatted extraction, preserves code blocks)
- `WebFetch` — low fidelity (summarized, strips specifics) — NEVER for "how-to" implementation

See [Accessing Online Resources](./accessing_online_resources.md) for tool selection criteria and experimental evidence.

---

## Omission Rule

**When there is nothing session-specific to add, omit ECOSYSTEM CONTEXT entirely.**

The section only earns its place when it contains information the agent cannot find in CLAUDE.md, tool descriptions, or the project files it will read. An empty ECOSYSTEM CONTEXT or one filled with inherited context is worse than no section — it trains the orchestrator to fill boilerplate.

---

## Quick Reference

| Content type | Belongs in ECOSYSTEM CONTEXT? | Reason |
|---|---|---|
| Authenticated CLI state (`gh` is logged in) | YES | Session-specific, varies per run |
| Task-specific access (CI logs for PR #42) | YES | Specific to this delegation |
| Non-obvious doc location (`.tmp/reports/`) | YES | Saves discovery time |
| Runtime state (docker running, DB seeded) | YES | Varies per session |
| "Full project context available" | NO | Always true; inherited |
| "Check `<functions>` for MCP tools" | NO | In tool descriptions; inherited |
| "Activate relevant skills" | NO | In CLAUDE.md; inherited |
| "Maximize parallel execution" | NO | In CLAUDE.md; inherited |
| Toolchain conventions (uv, pnpm, cargo) | NO | In project CLAUDE.md; inherited |
| Generic MCP server list (Ref, context7, exa) | NO | In tool descriptions; inherited |
