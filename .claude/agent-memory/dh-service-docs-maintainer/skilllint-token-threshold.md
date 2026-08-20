---
name: skilllint-token-threshold
description: prek passing on a SKILL.md edit does not mean skilllint's 4400-token AS005/SK006 threshold still passes — re-run skilllint after every SKILL.md edit, not just once at the end
metadata:
  type: feedback
---

`uv run prek run --files <SKILL.md>` does not check the skilllint token-count thresholds (AS005
"body exceeds 4400 tokens", SK006 "skill body is large") — the plugin-validator hook it runs is a
separate, narrower check. A `SKILL.md` already sitting close to the 4400-token ceiling can cross it
from a single added sentence in a table cell, and prek will still report green.

**Why**: discovered while fixing a doc claim in `plugins/development-harness/skills/backlog/
SKILL.md` — a one-sentence correction pushed the file from clean to 4408 tokens (AS005 + SK006
both fired), even though prek passed throughout.

**How to apply**: after editing any `SKILL.md`, run `uvx skilllint@latest check <path>` directly
(not just prek) and treat AS005/SK006 warnings as a signal to tighten wording, not as acceptable
noise — they are warnings (exit 0) but still real regressions worth trimming for, especially when
the edit is a correction rather than new required content. Re-run after each trim; token count
does not shrink linearly with word count in an obvious way (chained edits took two trim passes
to clear the threshold in this case).
