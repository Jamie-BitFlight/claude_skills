# Orchestrator-Discipline Plugin — Additional Rules

Rules specific to this plugin's hooks and tooling. The full orchestrator context window discipline is in `../CLAUDE.md`.

---

## Tool Use Denial Protocol (HARD STOP)

When ANY tool use is denied by the user:

1. STOP the current action sequence immediately — do not execute any further tools
2. State exactly what was denied and what you cannot do without it:
   `BLOCKED — [action] was denied. I cannot [goal] without [what you needed].`
3. Do NOT invent alternative paths, workarounds, or equivalent approaches
4. Do NOT retry with modified commands that achieve the same denied goal
5. Ask the user what they want to do next

**Reason**: Permission denial is a user boundary signal, not a technical obstacle to route around. Inventing workarounds (e.g., `git show FETCH_HEAD:` after `git checkout` was denied, or `git worktree` to create a shadow workspace) violates user trust and operates outside the user's awareness.

SOURCE: Session forensics 2026-03-02, session e3280e97 — two `git checkout` denials bypassed via `git show` + `git worktree` workaround; user discovered this only after the model had implemented changes in `/tmp/`.

---

## Bash Built-In Tool Enforcement

The orchestrator MUST use built-in Claude Code tools instead of Bash equivalents for file operations. A blocking PreToolUse hook (`prevent-bash-tool-misuse.cjs`) enforces this at the tool-call level.

**Commands blocked by hook** (use built-in tool instead):

- `grep pattern file` — use `Grep(pattern="...", path="...")`
- `find . -name "*.ts"` — use `Glob(pattern="**/*.ts")`
- `ls /some/dir` — use `Glob(pattern="*", path="/some/dir")`
- `cat file.txt` — use `Read(file_path="/path/to/file")`
- `head -20 file` — use `Read(file_path="...", limit=20)`
- `tail -20 file` — use `Read(file_path="...", offset=-20)`
- `sed -n '10,30p' file` — use `Read(file_path="...", offset=10, limit=20)`

**Legitimate Bash patterns** (hook does not block):

- Pipeline uses: `git log | grep`, `uv run ... | head`, `gh ... | grep`
- `cat /dev/stdin`, `cat -` (reading stdin)
- `ls -la` (human-readable directory listing)

**Kaizen evidence**: 28 violations in session e3280e97 (2026-03-02) — a 233-turn session with 0 agent delegations. Each violation was individually small but collectively they consumed significant context and prevented delegation to fresh-context agents.

SOURCE: Session e3280e97 transcript analysis, 2026-03-02.
