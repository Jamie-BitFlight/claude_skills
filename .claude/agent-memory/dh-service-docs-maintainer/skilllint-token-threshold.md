---
name: skilllint-token-threshold
description: A green prek run on a SKILL.md edit can hide skilllint's SK006 token-size warning — run skilllint directly and read its warnings after each SKILL.md edit
metadata:
  type: feedback
---

prek runs `skilllint check --fix` on every `SKILL.md` under `plugins/` and `.claude/`, but SK006 (body over the token warning
threshold) is a warning: it exits 0 and prek reports green without printing it. The hook fails on
SK007 (the error threshold, error severity) and whenever it applies a fix.

After editing a `SKILL.md`, run `uvx skilllint@latest check <path>` and read the output. Treat a
new SK006 as a regression to trim, especially when the edit was a correction and not new required
content. Re-run after each trim.
