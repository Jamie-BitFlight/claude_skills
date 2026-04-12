---
name: the-rewrite-room
description: Use when auditing docs vs code drift, syncing docs after changes, optimizing CLAUDE.md or SKILL.md for AI consumption, validating GLFM and Markdown, or summarizing files/URLs/images — routes each task to the correct specialist agent via /rwr:audit, /rwr:optimize, or /rwr:author
allowed-tools: Read, Grep, Glob, Bash, Task, Write, Edit
---

# The Rewrite Room

Routes documentation, authoring, and optimization tasks to the correct specialist agents. Does not rewrite source agents or skills — orchestrates them. Governs authoring, docs, prompts, and summaries — not product code.

## Quick Start

```text
/rwr:audit "check if kaizen plugin docs match the code"
/rwr:optimize "plugins/plugin-creator/skills/add-doc-updater/SKILL.md"
/rwr:author "summarize plugins/summarizer/skills/summarizer/SKILL.md"
```

## Command Reference

| Command | Entry Agent | Use When |
|---------|-------------|----------|
| `/rwr:audit <task>` | rewrite-room-auditor | Docs vs code drift, doc sync after changes, freshness tracking |
| `/rwr:optimize <file>` | rewrite-room-optimizer | CLAUDE.md, SKILL.md, agent .md improvement |
| `/rwr:author <task>` | rewrite-room-author | User-facing docs, GLFM validation, summarization |
| `/rwr:cite <source URL> [key points] [content type]` | rewrite-room-cite | Source-attributed content writing with hyperlinked citations from URLs |
| `/rwr:doc-to-skill <docs_path> <output_plugin> <output_skill>` | rewrite-room-doc-converter | Convert user-facing docs directory into a Claude Code skill |

Each command loads the corresponding workflow file and follows its numbered steps.

## Workflow Index

```mermaid
flowchart TD
    User([User invokes /rwr:*]) --> Q{Which command?}
    Q -->|/rwr:audit| Audit[rewrite-room-auditor\nLoads: plugins/the-rewrite-room/the-rewrite-room/workflows/audit.md]
    Q -->|/rwr:optimize| Opt[rewrite-room-optimizer\nLoads: plugins/the-rewrite-room/the-rewrite-room/workflows/optimize.md]
    Q -->|/rwr:author| Auth[rewrite-room-author\nLoads: plugins/the-rewrite-room/the-rewrite-room/workflows/author.md]
    Q -->|/rwr:cite| Cite[rewrite-room-cite<br>Source-attributed content with citations]
    Q -->|/rwr:doc-to-skill| DocSkill[rewrite-room-doc-converter<br>Loads: plugins/the-rewrite-room/skills/user-docs-to-ai-skill/SKILL.md]
    Audit --> A1[development-harness:doc-drift-auditor]
    Audit --> A2[development-harness:service-docs-maintainer]
    Audit --> A3[doc-freshness-guardian]
    Opt --> O1[plugin-creator:contextual-ai-documentation-optimizer]
    Opt --> O2[plugin-creator:subagent-refactorer]
    Auth --> B1[gitlab-docs-expert]
    Auth --> B2[documentation-expert]
    Auth --> B3[summarizer:file-summarizer / summarizer:url-summarizer / summarizer:image-summarizer]
```

## Workflow Files

Each command agent loads the corresponding workflow file at runtime:

- Audit workflow: `plugins/the-rewrite-room/the-rewrite-room/workflows/audit.md`
- Optimize workflow: `plugins/the-rewrite-room/the-rewrite-room/workflows/optimize.md`
- Author workflow: `plugins/the-rewrite-room/the-rewrite-room/workflows/author.md`

Workflow files contain numbered steps, conditional branching, explicit agent spawn instructions, structured return handling, and output contracts.

## Adding New Workflows

Every rwr command requires four components. All four are mandatory — there are no exceptions. A command that exists in the table without a routing agent cannot be invoked.

```mermaid
flowchart TD
    Start([Add new /rwr:name command]) --> S1["Step 1: Create the skill\nplugins/the-rewrite-room/skills/<name>/SKILL.md\nThe skill IS the workflow — it contains the numbered steps,\nbranching logic, and agent delegation instructions"]
    S1 --> S2["Step 2: Create the routing agent\nplugins/the-rewrite-room/agents/rewrite-room-<name>.md\nThe agent is the router — it receives the command invocation,\nloads the skill, and delegates based on task type.\nFrontmatter: name, description, tools, model, color\nBody: role, task routing mermaid, output contract"]
    S2 --> S3["Step 3: Add command row to Command Reference table\nCommand column: /rwr:name\nEntry Agent column: rewrite-room-<name> (the AGENT name — not the skill name)\nUse When column: one-line description"]
    S3 --> S4["Step 4: Add branch to Workflow Index mermaid\nNew branch from Q node: /rwr:name -> rewrite-room-<name>\nNode label: agent name + what skill it loads"]
    S4 --> V{"Verification checklist\n(all 4 must pass before done)"}
    V -->|"❌ Any item fails"| Fix[Fix the missing item and re-verify]
    Fix --> V
    V -->|"✅ All pass"| Done([Command is complete])
```

**Verification checklist — all four required before the command is declared complete:**

- [ ] Agent file exists at `plugins/the-rewrite-room/agents/rewrite-room-<name>.md`
- [ ] `.claude-plugin/plugin.json` does NOT have an `agents` key (default-path agents are auto-discovered; writing the key would mask the rest)
- [ ] Command row in Command Reference table — Entry Agent column contains the agent name (not the skill name)
- [ ] Branch in Workflow Index mermaid points to the agent node (not the skill directory)

> **⚠️ plugin.json auto-discovery — if registering this agent in plugin.json**
>
> Agents in the default `agents/` directory are auto-discovered. Do NOT add them to plugin.json.
>
> If the agent is in a non-default location and must be declared:
> - Read the existing `agents` array in plugin.json first
> - Carry forward every existing entry — adding one without listing all others makes the rest invisible
> - It is all or nothing

**Skill vs agent — the distinction that prevents the missing-agent failure:**

- The **skill** (`skills/<name>/SKILL.md`) contains the workflow: numbered steps, conditional logic, specialist agent delegation
- The **routing agent** (`agents/rewrite-room-<name>.md`) is the entry point: it receives the `/rwr:name` invocation, loads the skill, and executes it
- A skill alone cannot receive a command invocation — it must be loaded by an agent
- `user-docs-to-ai-skill` is a skill name, not an agent name — it cannot appear in the Entry Agent column

## Source Components

This plugin routes to these specialist agents and scripts (not copied — referenced by path):

**Audit agents:**

- `plugins/development-harness/agents/doc-drift-auditor.md` — evidence-based drift audit with file:line citations
- `plugins/development-harness/agents/service-docs-maintainer.md` — post-implementation doc sync via git diff
- `~/.claude/agents/doc-freshness-guardian.md` — freshness headers and staleness alerts (personal agent, not bundled with this plugin)

**Optimize agents:**

- `plugins/plugin-creator/agents/contextual-ai-documentation-optimizer.md` — RT-ICA + CoVe prompt optimization with token impact reporting
- `plugins/plugin-creator/agents/subagent-refactorer.md` — Anthropic official best practices refactoring with mandatory research phase

**Author agents:**

- `gitlab-docs-expert` — GitLab Wiki, MR descriptions, GitLab README authoring
- `documentation-expert` — general README, tutorials, API docs, user-facing docs

**Citation agent:**

- `plugins/the-rewrite-room/agents/rewrite-room-cite.md` — source-attributed content writer with primary source verification and hyperlinked citations

**Summarizer agents:**

- `plugins/summarizer/agents/file-summarizer.md` — file content summarization with fidelity enforcement
- `plugins/summarizer/agents/url-summarizer.md` — URL content summarization
- `plugins/summarizer/agents/image-summarizer.md` — image/screenshot description

**Validation scripts:**

- `plugins/gitlab-skill/skills/gitlab-skill/scripts/validate_glfm.py` — GitLab Flavored Markdown validation via GitLab API
- `plugins/plugin-creator/scripts/normalize_frontmatter.py` — YAML frontmatter schema validation

**Reference files consulted by workflows:**

- `plugins/summarizer/skills/summarizer/references/fidelity-rules.md` — summarizer fidelity rules
- `plugins/gitlab-skill/skills/gitlab-skill/references/glfm-syntax.md` — GLFM syntax reference
- `plugins/plugin-creator/skills/prompt-optimization/SKILL.md` — prompt optimization principles
