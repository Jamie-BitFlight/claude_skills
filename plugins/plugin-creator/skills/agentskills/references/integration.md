# Integrating Agent Skills into Your Agent

> Source: <https://agentskills.io/integrate-skills.md>

**Use this guide when** building or modifying an AI agent or development tool to support the Agent Skills format — discovering skills, loading metadata, injecting into context, and handling script execution safely.

This guide explains how to add skills support to an AI agent or development tool.

---

## Contents

- [Integration approaches](#integration-approaches)
- [Overview](#overview)
- [Skill discovery](#skill-discovery)
- [Cloud-hosted and sandboxed agent discovery](#cloud-hosted-and-sandboxed-agent-discovery)
- [Loading metadata](#loading-metadata)
- [Injecting into context](#injecting-into-context)
- [Structured wrapping for dedicated activation tools](#structured-wrapping-for-dedicated-activation-tools)
- [Security considerations](#security-considerations)
- [Trust gates for project-level skills](#trust-gates-for-project-level-skills)
- [Permission allowlisting for bundled resources](#permission-allowlisting-for-bundled-resources)
- [Subagent delegation (advanced, optional)](#subagent-delegation-advanced-optional)
- [Reference implementation](#reference-implementation)

---

## Integration Approaches

**Filesystem-based agents** operate within a computer environment (bash/unix). Skills are activated when models issue shell commands like `cat /path/to/my-skill/SKILL.md`. Bundled resources are accessed through shell commands. This is the most capable option.

**Tool-based agents** function without a dedicated computer environment. They implement tools allowing models to trigger skills and access bundled assets. The specific tool implementation is up to the developer.

---

## Overview

A skills-compatible agent needs to:

1. **Discover** skills in configured directories
2. **Load metadata** (name and description) at startup
3. **Match** user tasks to relevant skills
4. **Activate** skills by loading full instructions
5. **Execute** scripts and access resources as needed

---

## Skill Discovery

Skills are folders containing a `SKILL.md` file. The agent should scan configured directories for valid skills.

---

## Cloud-Hosted and Sandboxed Agent Discovery

Filesystem-based discovery assumes the agent has access to the local filesystem. For agents running in containers, VMs, or cloud sandboxes this assumption does not hold. Three approaches cover the non-filesystem case:

- **Project-level skills travel with code** — Skills committed to a repository are available even in sandboxed environments because the repository is cloned into the sandbox. No extra provisioning is needed for project-level skills.
- **User-level skills need external provision** — Skills stored at the user level (e.g., `~/.claude/skills/`) are not present in a fresh sandbox. Provision them by cloning a config repository into the sandbox before agent startup, providing skill URLs the agent can fetch, or offering a web UI where users upload skills before starting a session.
- **Built-in skills as static deployment artifacts** — Skills that the product ships as part of its deployment image are always available in any sandbox. Package commonly needed skills as static assets in the deployment.

SOURCE: [agentskills.io integration guide](https://agentskills.io/integrate-skills.md) (accessed 2026-08-24)

---

## Loading Metadata

At startup, parse only the frontmatter of each `SKILL.md` file. This keeps initial context usage low.

### Parsing Frontmatter

```
function parseMetadata(skillPath):
    content = readFile(skillPath + "/SKILL.md")
    frontmatter = extractYAMLFrontmatter(content)

    return {
        name: frontmatter.name,
        description: frontmatter.description,
        path: skillPath
    }
```

---

## Injecting into Context

Include skill metadata in the system prompt so the model knows what skills are available.

For Claude models, the recommended format uses XML:

```xml
<available_skills>
  <skill>
    <name>pdf-processing</name>
    <description>Extracts text and tables from PDF files, fills forms, merges documents.</description>
    <location>/path/to/skills/pdf-processing/SKILL.md</location>
  </skill>
  <skill>
    <name>data-analysis</name>
    <description>Analyzes datasets, generates charts, and creates summary reports.</description>
    <location>/path/to/skills/data-analysis/SKILL.md</location>
  </skill>
</available_skills>
```

**For filesystem-based agents:** Include the `location` field with the absolute path to the SKILL.md file.

**For tool-based agents:** The location can be omitted.

Keep metadata concise. Each skill should add roughly 50-100 tokens to the context. **Reason:** This keeps the system prompt within typical limits for skill discovery; excessive metadata can cause truncation and prevent skills from being auto-invoked.

---

## Structured Wrapping for Dedicated Activation Tools

When using a dedicated tool (rather than filesystem commands) to activate a skill, wrap skill content in XML tags so the model can distinguish it from other context and the harness can identify it during context compaction.

```xml
<skill_content name="pdf-processing">
  Skill directory: /path/to/skills/pdf-processing/
  Relative paths in this skill are relative to the skill directory.

  <skill_resources>
    references/forms.md
    references/api.md
    scripts/extract.py
    assets/template.docx
  </skill_resources>
</skill_content>
```

SOURCE: [agentskills.io integration guide](https://agentskills.io/integrate-skills.md) (accessed 2026-08-24)

---

## Security Considerations

Script execution requires safeguards to remain safe:

- **Sandboxing** — Run scripts in isolated environments
- **Allowlisting** — Execute scripts only from trusted skills
- **Confirmation** — Ask users before running potentially dangerous operations
- **Logging** — Record all script executions for auditing

---

## Trust Gates for Project-Level Skills

Project-level skills (committed to a repository) can come from untrusted sources when users open third-party repositories. Without a trust check, a malicious repository could inject skill instructions that execute arbitrary operations.

**Recommended approach:** Gate project-level skill loading on an explicit trust signal — for example, requiring the user to mark a directory as trusted before its skills are loaded into context. This prevents untrusted repositories from injecting instructions automatically.

SOURCE: [agentskills.io integration guide](https://agentskills.io/integrate-skills.md) (accessed 2026-08-24)

---

## Permission Allowlisting for Bundled Resources

When an agent uses a permission system that prompts the user before file reads, bundled skill resources (files in `references/`, `scripts/`, `assets/`) will each trigger a permission dialog unless the skill directory is explicitly allowlisted.

**Recommended approach:** When a skill is loaded, add its directory to the agent's read-permission allowlist so the model can access bundled resources without interrupting the user for each file. Without allowlisting, every reference file access produces a confirmation prompt that breaks the user experience.

SOURCE: [agentskills.io integration guide](https://agentskills.io/integrate-skills.md) (accessed 2026-08-24)

---

## Subagent Delegation (Advanced, Optional)

Some agent implementations support running a skill in a separate subagent session. In this pattern:

1. The main agent receives a user request and identifies the relevant skill.
2. The skill is loaded into a fresh subagent session with the full task as its prompt.
3. The subagent executes the skill workflow and returns a summary to the main conversation.

This is useful for complex skill workflows that benefit from an isolated context window. Support for subagent delegation is optional and varies between agent implementations.

SOURCE: [agentskills.io integration guide](https://agentskills.io/integrate-skills.md) (accessed 2026-08-24)

---

## Reference Implementation

The [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) library provides Python utilities and a CLI for working with skills.

**Validate a skill directory:**

```bash
skills-ref validate <path>
```

**Generate `<available_skills>` XML for agent prompts:**

```bash
skills-ref to-prompt <path>...
```

Use the library source code as a reference implementation for building your own skills integration.

---

## Adoption

Agent Skills has been adopted by a growing number of agent products, including Claude Code, Cursor, VS Code, Gemini CLI, OpenAI Codex & Copilot, Roo Code, Amp, Goose, Factory, and Databricks. See the live client showcase at <https://agentskills.io> for the current full list.
