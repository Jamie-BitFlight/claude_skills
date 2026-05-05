# Frontmatter Generation

**Actor**: Claude (executing the research-curator skill workflow)
**Entry**: Path to `./research/{category}/{name}.md`
**Outcome**: File begins with canonical YAML frontmatter block; `prek` exits 0

---

## Canonical Schema

```yaml
---
title: "{Official resource name}"
subtitle: "{What a reader finds inside — 5–10 words, written as a journal deck line}"
category: "{parent directory name}"
resource_url: "{primary URL}"
github_url: "{GitHub URL — omit field entirely if absent}"
date_created: "YYYY-MM-DD"
date_last_reviewed: "YYYY-MM-DD"
status: "published"
---
```

---

## Procedure

**1. Read** — read the complete entry file before extracting any field. Values appear in the body; reading first is required, not optional.

**2. Skip check** — if the file already has all of `title`, `subtitle`, `category`, `resource_url`, `date_created`, `date_last_reviewed`, `status` present and non-empty: stop, report SKIPPED, do not write.

**3. Extract** — apply the extraction table. Required fields are `title` and `resource_url`; all others have defined fallbacks.

| Field | Where to find it |
|---|---|
| `title` | YAML `title:` or `name:` → else first `# Heading` |
| `subtitle` | YAML `subtitle:` → else after reading the full entry, write 5–10 words describing what a reader finds inside — the key capability, finding, or differentiator — as a journal editor would pitch the article |
| `category` | YAML `category:` or `metadata.category:` → else parent directory name |
| `resource_url` | YAML `resource_url:` or `metadata.source_url:` → else `**Source URL**: <url>` in body |
| `github_url` | YAML `github_url:` or `metadata.github:` (add `https://github.com/` if no scheme) → else `**GitHub Repository**: <url>` → **omit field entirely** if absent |
| `date_created` | YAML `date_created:` or `created:` or `metadata.verified:` → else `**Research Date**: YYYY-MM-DD` in body → else `git log --follow --diff-filter=A --format='%as' -- {path} \| tail -1` |
| `date_last_reviewed` | YAML `date_last_reviewed:` or `last_reviewed:` → else `Last Verified \| YYYY-MM-DD` in Freshness Tracking table → else same as `date_created` |
| `status` | Always `published` |

**4. Write** — quote all date values (`"2026-05-02"`, not `2026-05-02`). Then:

- **No existing frontmatter** (no `---` at line 1): prepend `---\n{fields}\n---\n` before the first line of body content
- **Existing frontmatter present**: replace the entire block between the opening and closing `---` delimiters; leave all body content after the closing `---` unchanged

**5. Verify** — read back the first 10 lines and confirm: opening `---` on line 1, closing `---` present, `title:` field visible. Then run:

```bash
uv run prek run --files ./research/{category}/{name}.md
```

---

## Error Paths

- `title` or `resource_url` unresolvable from all fallbacks → report UNRESOLVABLE with the file path, do not write any frontmatter, stop
- `prek` exits non-zero → read the full error output, fix the specific violation, re-run prek; do not mark done until exit 0

---

## Examples

**Before** (no frontmatter — Format A):

```markdown
# ESP-CLAW: Chat-Coding AI Agent Framework for IoT Devices

**Research Date**: 2026-05-02
**Source URL**: <https://esp-claw.com/>
**GitHub Repository**: <https://github.com/espressif/esp-claw>

## Overview

ESP-CLAW is Espressif's event-driven AI agent framework...
```

**After**:

```yaml
---
title: ESP-CLAW
subtitle: Chat-Coding AI Agent Framework for ESP32 IoT Devices
category: agent-frameworks
resource_url: https://esp-claw.com/
github_url: https://github.com/espressif/esp-claw
date_created: "2026-05-02"
date_last_reviewed: "2026-05-02"
status: published
---
```

---

**Before** (nested metadata — Format C):

```yaml
---
name: Agno
description: Agno is a Python framework for building multi-agent systems...
metadata:
  category: agent-frameworks
  source_url: https://docs.agno.com
  github: agno-agi/agno
  verified: "2026-01-31"
---
```

**After**:

```yaml
---
title: Agno
subtitle: Python framework for building multi-agent systems
category: agent-frameworks
resource_url: https://docs.agno.com
github_url: https://github.com/agno-agi/agno
date_created: "2026-01-31"
date_last_reviewed: "2026-01-31"
status: published
---
```
