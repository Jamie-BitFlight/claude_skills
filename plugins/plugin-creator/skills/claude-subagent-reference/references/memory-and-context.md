# Memory, Context, and Isolation

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Enable persistent memory (accessed 2026-05-28)
SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Manage subagent context (accessed 2026-05-28)
SOURCE: <https://code.claude.com/docs/en/worktrees.md> § Isolate subagents with worktrees (accessed 2026-05-28)

---

## What loads at subagent startup

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § What loads at startup (accessed 2026-05-28)

Each subagent starts with a fresh, isolated context window — no conversation history, no previously invoked skills, no previously read files. Claude composes a delegation message that summarizes the task, and the subagent works from there.

| Element | Loaded? | Notes |
|:--------|:--------|:------|
| System prompt | Yes | Agent's own prompt (markdown body or `prompt` field) + environment details. NOT the full Claude Code system prompt |
| Task message | Yes | The delegation prompt Claude writes when handing off the work |
| CLAUDE.md and memory | Yes | Every level of the memory hierarchy the main conversation loads. **Explore and Plan skip this** |
| Git status | Yes | Snapshot from the start of the parent session. **Explore and Plan skip this** |
| Preloaded skills | Only if listed in `skills` field | Full content injected. Built-in agents don't preload skills |
| Main conversation history | No | Subagents start fresh. Exception: forks inherit full history — see [./fork-mode.md](./fork-mode.md) |

Explore and Plan omit `CLAUDE.md` and git status. Custom subagents can set `omitClaudeMd: true` to omit user, project, and local `CLAUDE.md` files.

If a rule must reach a subagent (e.g., "ignore the `vendor/` directory"), restate it in the delegation prompt — the main conversation reads Explore and Plan results with full CLAUDE.md context, so most rules don't need to reach the subagent itself.

---

## Persistent memory

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Enable persistent memory (accessed 2026-05-28)

The `memory` field gives the subagent a persistent directory that survives across conversations, letting it accumulate knowledge over time (codebase patterns, debugging insights, architectural decisions).

```yaml
memory: project
```

| Scope | Location | Use when |
|:------|:---------|:---------|
| `user` | `~/.claude/agent-memory/<name-of-agent>/` | Knowledge should apply across all projects |
| `project` | `.claude/agent-memory/<name-of-agent>/` | Knowledge is project-specific; shareable via version control |
| `local` | `.claude/agent-memory-local/<name-of-agent>/` | Knowledge is project-specific but must not be checked in |

**Recommended default**: `project` — shareable via version control.

### What enabling memory does

When `memory` is set:

- The subagent's system prompt includes instructions for reading and writing to the memory directory
- The first 200 lines or 25 KB of `MEMORY.md` in the memory directory is injected into the system prompt (whichever comes first), with instructions to curate `MEMORY.md` if it exceeds that limit
- `Read`, `Write`, and `Edit` tools are automatically enabled so the subagent can manage its memory files

### Tips for persistent memory

- Ask the subagent to consult its memory before starting work: "Review this PR, and check your memory for patterns you've seen before."
- Ask the subagent to update its memory after completing a task: "Now that you're done, save what you learned to your memory."
- Include memory update instructions in the subagent's markdown body so it proactively maintains its knowledge base.

---

## Worktree isolation

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Supported frontmatter fields — isolation (accessed 2026-05-28)
SOURCE: <https://code.claude.com/docs/en/worktrees.md> § Isolate subagents with worktrees (accessed 2026-05-28)

```yaml
isolation: worktree
```

Runs the subagent in a temporary git worktree — an isolated copy of the repository branched from your default branch (`origin/HEAD` by default). Edits in the worktree never touch files in your main checkout.

The worktree is automatically cleaned up when the subagent finishes **if no changes were made**. If changes exist, Claude prompts to keep or remove.

> `isolation: worktree` is the only supported `isolation` value. It is also valid in plugin subagents (it is the only `isolation` value plugin agents support).

### Choosing the base branch

Worktrees branch from `origin/HEAD` by default. To branch from your current local `HEAD` instead (carrying unpushed commits and feature-branch state):

```json
{
  "worktree": {
    "baseRef": "head"
  }
}
```

### Copying gitignored files into worktrees

A worktree is a fresh checkout — untracked files like `.env` are absent. To copy them automatically, add `.worktreeinclude` to your project root (uses `.gitignore` syntax; only gitignored files matching a pattern are copied):

```text
.env
.env.local
config/secrets.json
```

---

## Resume subagents

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Resume subagents (accessed 2026-05-28)

Resumed subagents retain their full conversation history. Ask Claude to continue previous work:

```
Use the code-reviewer subagent to review the authentication module
[Agent completes]

Continue that code review and now analyze the authorization logic
[Claude resumes the subagent with full context from previous conversation]
```

Claude Code can resume or follow up with a subagent through the Agent workflow. `SendMessage` is also documented for follow-up and does not require agent teams.

Subagent transcripts are stored at:
`~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`

If a stopped subagent receives a `SendMessage`, it auto-resumes in the background without requiring a new `Agent` invocation.

SOURCE: <https://code.claude.com/docs/en/sub-agents#choose-a-model> (accessed 2026-09-24)

---

## Auto-compaction

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Auto-compaction (accessed 2026-05-28)

Subagents support auto-compaction using the same logic as the main conversation. Default trigger: approximately 95% context capacity.

Override the trigger threshold:

```bash
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50   # trigger at 50% instead
```

Compaction events appear in the subagent transcript file as entries with `"type": "system"`, `"subtype": "compact_boundary"`, and a `compactMetadata.preTokens` field showing token count before compaction.

Main conversation compaction does not affect subagent transcripts — they are stored in separate files.

### Transcript cleanup

Transcripts are cleaned up automatically based on `cleanupPeriodDays` (default: 30 days). You can find the agent ID for resumption in the transcript path or by asking Claude for it.
