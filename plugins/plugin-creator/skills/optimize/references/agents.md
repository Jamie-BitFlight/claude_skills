# Agents — What Belongs in an Agent File

SOURCE: [claude-plugins-official plugin-dev skill — agent-development](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/plugin-dev/skills/agent-development) (accessed 2026-03-10)

An agent file is a system prompt. It describes what the agent is, what it produces, and any constraints specific to its role. It is not a tutorial, a reference document, or a duplicate of the skill that invokes it.

## What to Write

**Role** — what this agent is. One sentence.

**Output** — what it produces and in what form. Specific enough that another session can verify it.

**Project-specific constraints** — things the agent would not know from training. "Write findings to `.claude/reports/`." "Use the task file path passed in the prompt — do not search for it."

**Stopping conditions** — when to stop and report rather than continue. Agents that keep going when blocked are expensive.

## What Not to Write

**Domain knowledge Claude already has** — the agent does not need to be told how to read a file, parse YAML, or run a shell command. It knows.

**Procedures the skill already defines** — if the skill that invokes this agent covers a workflow, the agent file should not re-describe it. The skill sets context; the agent executes.

**Examples of standard operations** — an example showing non-obvious output format is useful. Examples showing how to use Read tool or how to check exit codes are not.

**Boilerplate role descriptions** — "You are a highly capable AI assistant specializing in..." adds no information. State the specific role.

**Invented quality standards** — "Ensure all code follows SOLID principles" as a generic instruction is noise. Write only standards that are verified requirements of this project.

## Size Signal

If the agent file is longer than the skill that uses it, the agent is carrying content that belongs in the skill's references/. An agent file that works standalone without its skill is probably duplicating the skill's knowledge layer.

## When Optimizing an Agent File

For each block of content in the agent that isn't role, output, project-specific constraints, or stopping conditions:

1. **Is it domain reference material?** → candidate for a skill's `references/` file. If the agent is in a plugin, check whether an existing skill in that plugin already covers the topic. If yes, merge into it. If no, create a new reference file under the most relevant skill.

2. **Is it a workflow or procedure?** → candidate for a `SKILL.md` body. The skill invokes the agent; the agent shouldn't carry the workflow.

3. **Is it discoverable or derivable?** → cut it entirely. Do not move it.

For plugin agents: run `Glob("skills/*/SKILL.md", path="{plugin_dir}")` to see existing skills before deciding whether to create a new one or extend an existing one.
