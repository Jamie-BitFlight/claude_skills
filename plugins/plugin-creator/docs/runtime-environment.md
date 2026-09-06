# Runtime environment: what a distributed plugin may reference

Every sentence you write has one of two audiences.

**Runtime** — the agent executing the artifact, doing the task the artifact exists for. It reads
`SKILL.md` bodies, agent bodies, and `references/`.

**Design-time** — whoever edits the source later. It reads `MAINTENANCE.md`, ADRs, and commit
messages. The executing agent never sees these.

## The environment split

The runtime agent does not run where you authored the artifact. Your plugin gets installed into
a repo that never had your source tree. A path into your tree resolves for you and for nobody
else, so the failure reaches your users and never reaches you.

## The three-part check

Before writing any path, command, or fact into runtime text, confirm one of these:

1. It is present in every environment — a stdlib module, a POSIX command, a tool your
   frontmatter declares.
2. It is one of your own bundled files, reached by a relative path from the skill root.
3. It is inlined right there, needing no lookup.

If none hold, inline it, move it into your plugin's `references/`, or delete it.

## Harness substitutions

Part 2 says *relative path* because that is the only form the specification defines. The Agent
Skills specification, under "File references", says: "When referencing other files in your
skill, use relative paths from the skill root." It defines no substitution variables.

A substitution variable is therefore a bet on which harness reads your skill. Each one below is
that harness's own extension, not a shared convention:

| Harness | Variable | Where it substitutes | Confirmed |
|---|---|---|---|
| Claude Code | `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PLUGIN_ROOT}` | the skill's markdown body and `allowed-tools` only — never `references/` | vendor docs |
| Kimi Code | `${KIMI_SKILL_DIR}` | skill body | reported, unconfirmed |
| Pi | `{baseDir}` | skill body | reported, unconfirmed |
| Agent Plugins | `${PLUGIN_ROOT}` | `mcp.json` args, env and cwd only | reported, unconfirmed |

Harnesses absent from this table are absent because nobody has looked, not because they were
checked and found to substitute nothing. Treat a blank as unknown.

What a harness that does not substitute a variable *does* with the literal string is also
unknown — it may pass it through, drop it, or error, and no source consulted says which.
That uncertainty is the argument: a relative path needs no such knowledge. Reach for a variable
only when you know the harness reads it, and take a relative path otherwise.

## Four failures

A link climbing out of the plugin:

```markdown
See [the delegation rule](../../../../rules/delegation.md).
```

Nothing is at that path once installed. Inline the rule, or bundle it.

An unconditional load of another plugin's skill:

```markdown
Load the other-plugin:analyzer skill, then apply its output.
```

That plugin may not be installed. Make it conditional, or drop the dependency.

Maintainer advice inside runtime text:

```markdown
We moved this in #412 after the old parser broke on nested fences.
```

The executing agent cannot act on it. It belongs in `MAINTENANCE.md`.

A repo-level hook described as if it shipped:

```markdown
The pre-commit hook validates your output before it is written.
```

Your consumer has no such hook. State what the agent must do itself.

## Generic examples

Name a shape with angle brackets — `<plugin>/skills/<name>/SKILL.md` — so nothing resolves it
and nothing can break. Put an illustrative real path inside a fenced block, where it reads as
an example rather than an instruction. Inline code spans and table cells do not get that
latitude; a path there reads as a real one.
