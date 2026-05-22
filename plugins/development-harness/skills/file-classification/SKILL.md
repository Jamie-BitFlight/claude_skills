---
name: file-classification
description: Classifies changed files into review treatment tiers before any reviewer decides SKIP. Prevents reviewers from misclassifying LLM prompt engineering artifacts (agents/*.md, skills/*/SKILL.md, CLAUDE.md, rules/*.md) as documentation-only. Load this skill when reviewing any diff that contains markdown or prose files. Authoritative definition is verdict-schema.md §2.5.
user-invocable: false
---

# File Classification for Review

**Invoke before deciding SKIP on any prose file.** Three tiers determine which SKIP rules apply.

## Tier Decision

```mermaid
flowchart TD
    File([Changed file]) --> Q1{"Is it prose?<br>(markdown, text, config with prose fields)"}
    Q1 -->|"No — pure code"| Code["Standard review — apply perspective normally"]
    Q1 -->|Yes| Q2{"Does any part describe or influence<br>a process or function?"}
    Q2 -->|"No — pure reference data,<br>changelogs, release notes"| T1["Tier 1 — Documentation Only<br>SKIP permitted for all perspectives"]
    Q2 -->|"Yes — guides behavior, defines<br>constraints, describes a workflow"| Q3{"Primary executor or<br>audience is an AI / LLM / agent?"}
    Q3 -->|"No — human-facing<br>CONTRIBUTING.md, ADRs, runbooks"| T2["Tier 2 — Process Documentation<br>SKIP with explicit skip_reason only"]
    Q3 -->|"Yes — agent files, SKILL.md,<br>CLAUDE.md, rules/*.md, prompts"| T3["Tier 3 — LLM Prompt Engineering Artifact<br>See rules below"]
```

## Tier Rules

**Tier 1 — Documentation Only**

Changelogs, release notes, README sections describing completed features. SKIP is valid for
all perspectives with no applicable checks.

**Tier 2 — Process Documentation**

`CONTRIBUTING.md`, ADRs, runbooks, README workflow sections. These are behavioral contracts
for human contributors. SKIP is permitted only with an explicit `skip_reason` explaining why
the change has no impact in this reviewer's scope.

**Tier 3 — LLM Prompt Engineering Artifacts**

The markdown content IS the executable. These files are the product, not descriptions of it.

Tier 3 file patterns:

- `agents/*.md` — plugin agent instruction files
- `skills/*/SKILL.md` — skill instruction files
- `skills/*/references/**` — skill reference files (any depth)
- `CLAUDE.md` — session instruction files
- `.claude/rules/*.md` — scoped behavioral rules

Per-perspective SKIP rules for Tier 3:

| Perspective | SKIP | Required check |
|---|---|---|
| Security | **PROHIBITED** | Prompt injection surfaces — see §2.5.1 in `verdict-schema.md` |
| Quality | **PROHIBITED** | Behavioral correctness: contradictions, ambiguous constraints, missing edge cases |
| Performance | Permitted | No applicable performance check |
| Accessibility | Permitted | No applicable accessibility check |

For the full classification rule definition and the prompt injection surface checklist
(`§2.5.1`), read:
[verdict-schema.md §2.5](../multi-perspective-review/references/verdict-schema.md)
