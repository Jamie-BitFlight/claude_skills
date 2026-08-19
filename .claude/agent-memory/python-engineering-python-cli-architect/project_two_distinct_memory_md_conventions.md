---
name: two-distinct-memory-md-conventions
description: AGENTS.md's "do NOT use MEMORY.md files" rule (bd Issue Tracker section) is about a different, deprecated project-root convention, not the sanctioned .claude/agent-memory/{agent}/MEMORY.md index this agent maintains
metadata:
  type: project
---

This repo has two unrelated things both called "MEMORY.md":

1. A deprecated project-root convention for backlog/issue persistent knowledge,
   explicitly banned by `AGENTS.md`'s "Beads Issue Tracker" > "Rules" section:
   "Use `bd remember` for persistent knowledge — do NOT use `MEMORY.md` files."
2. The sanctioned per-specialist-agent memory index at
   `.claude/agent-memory/{agent-name}/MEMORY.md` — the system this very agent
   (`python-engineering-python-cli-architect`) is instructed to write to every
   session (see this agent's own system-prompt "Persistent Agent Memory"
   section). `AGENTS.md` itself cites a file from this exact directory as an
   authoritative source (line ~227), and `git log` on any agent's `MEMORY.md`
   shows a long, continuously-merged commit history of this pattern already on
   `main`.

**Why:** GitHub Copilot's automated review on PR #2987 flagged an addition to
`.claude/agent-memory/python-engineering-python-cli-architect/MEMORY.md` as
violating AGENTS.md's rule 1 above — a plausible-sounding but incorrect
conflation of the two systems. Investigated and determined NOT APPLICABLE;
no revert applied (see PR #2987 review thread reply, comment id 3809135385).

**How to apply:** If a reviewer (human or bot) flags a `.claude/agent-memory/**/MEMORY.md`
edit as violating the bd-remember rule, verify which "MEMORY.md" the citation
actually targets before acting — check the rule's surrounding section header
in AGENTS.md, and check whether the flagged path has prior merged history
under the same pattern.
