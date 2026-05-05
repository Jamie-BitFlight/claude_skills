# Frontmatter Generation

**Read the full entry file before writing any frontmatter field.** Title, subtitle, URL, and dates all appear in the body — extracting them without reading first produces wrong values.

## Canonical Schema

```yaml
---
title: "{Official resource name}"
subtitle: "{What it is — 5–10 words}"
category: "{parent directory name}"
resource_url: "{primary URL}"
github_url: "{GitHub URL — omit field if absent}"
date_created: "YYYY-MM-DD"
date_last_reviewed: "YYYY-MM-DD"
status: "published"
---
```

## Field Extraction

| Field | Where to find it |
|---|---|
| `title` | YAML `title:` or `name:` → else first `# Heading` |
| `subtitle` | YAML `subtitle:` → else first sentence of `## Overview` |
| `category` | YAML `category:` or `metadata.category:` → else parent directory name |
| `resource_url` | YAML `resource_url:` or `metadata.source_url:` → else `**Source URL**: <url>` in body |
| `github_url` | YAML `github_url:` or `metadata.github:` (prefix `https://github.com/` if no scheme) → else `**GitHub Repository**: <url>` → omit if not found |
| `date_created` | YAML `date_created:` or `created:` or `metadata.verified:` → else `**Research Date**: YYYY-MM-DD` in body → else `git log --follow --diff-filter=A --format='%as' -- {path} \| tail -1` |
| `date_last_reviewed` | YAML `date_last_reviewed:` or `last_reviewed:` → else `Last Verified \| YYYY-MM-DD` row in Freshness Tracking table → fallback to `date_created` |
| `status` | Always `published` |

## Examples

**Before** (Format A — no frontmatter):

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

**Before** (Format C — Agno nested metadata):

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

## Writing Rules

1. Omit `github_url` entirely when not found — do not write `github_url: ""`
2. Quote date values — `"2026-05-02"` not `2026-05-02`
3. Skip entries during `--add-frontmatter all` that already have all canonical fields present and non-empty
4. After writing, read back the first 10 lines to confirm `---` delimiters are present

## Validate

```bash
uv run prek run --files ./research/{category}/{name}.md
```
