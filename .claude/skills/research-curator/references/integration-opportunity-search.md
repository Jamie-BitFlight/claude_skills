# Integration Opportunity Search (preserved procedure — not currently wired)

This is Phase 2 of the deleted `research-context-agent`'s process, carried forward verbatim. It is
a **partial** carry-forward, not an equivalent-content replacement: PR #3529 deleted the agent,
and only the Phase 2 search procedure (the six-dimension table and the five-step search order) plus
Critical Rules 1 and 3 are reproduced below. Everything else in that agent is recoverable only from
git — Phase 1 (Absorb), Phase 3 (Append) and its `## Integration Opportunities` output schema,
Critical Rules 2, 4, 5 and 6, Input Format, Output Format, Quality Gates, Error Handling, the
worked Example Workflow, and Related.

The dropped Phase 3 schema is in live use: six entries under `./research/` carry an
`## Integration Opportunities` section written to it, so regenerating one means recovering that
schema from the git blob cited below first.

Why the agent was removed: its Phase 3 write path — `/process-research-integration`, whose script
`process_file()` returned `status="not_implemented"` — never wrote a byte, and no skill, command,
or workflow in the repo spawned the agent. It was a registered subagent type, so it remained
directly spawnable by name via the Agent tool; what it lacked was an automated caller, not every
invocation path.

Nothing currently invokes this file — it is reference material for a future redesign of the
integration search, not an active workflow step.

The deleted agent's own framing: search the repository for connections between one research file's
content and this repo's existing skills, agents, hooks, commands, and MCP servers, across the six
dimensions below.

## Dimensions

| Dimension | What to Look For | Where to Search |
|-----------|------------------|-----------------|
| **Enhance existing skills** | Could this research improve a skill's capability, accuracy, or coverage? | `**/skills/*/` (entire skill directories with SKILL.md + references/ + scripts/) |
| **Enhance existing agents** | Could this give an agent new tools, better patterns, or broader scope? | `**/agents/*.md` (both `.claude/agents/` and `plugins/*/agents/`) |
| **Enhance existing hooks** | Could this improve session lifecycle, validation, or automation? | `**/hooks/*` (both `.claude/hooks/` and `plugins/*/hooks/`) |
| **Enhance existing commands** | Could this research improve command functionality or add new capabilities? | `**/commands/*.md` (both `.claude/commands/` and `plugins/*/commands/`) |
| **New skill candidate** | Does this describe a workflow/technique/toolchain warranting its own skill? | Compare against ALL existing skills — only propose if no skill covers it |
| **New MCP server candidate** | Does this expose an API/data source valuable as a Claude Code MCP integration? | `**/.mcp.json`, `research/mcp-ecosystem/`, `plugins/fastmcp-creator/` |

## Search order

1. Use the Grep tool to search for related keywords in skills, agents, hooks, and commands.
2. Use the Glob tool to find relevant files by pattern.
3. Read the most relevant files to understand their current scope.
4. Validate claims against primary sources — prefer MCP tools (`ref_search_documentation`,
   `ref_read_url`, context7, exa) when available; fall back to WebSearch/WebFetch in sandboxed
   environments.
5. Identify specific, concrete enhancement opportunities with verified details.

## Critical rules (the deleted agent's Rules 1 and 3)

1. **Concrete over vague** — "Could enhance the holistic-linting skill by adding jscpd duplicate
   detection as a pre-lint step" NOT "Could be useful for code quality".
2. **No false positives** — Only include matches where there's a genuine, specific connection.
   Fewer high-quality matches beat many weak ones.

SOURCE: `.claude/agents/research-context-agent.md` as it existed at `main` before PR #3529 deleted
it (git blob `5987c6e69`, retrievable via `git show 5987c6e69`).
