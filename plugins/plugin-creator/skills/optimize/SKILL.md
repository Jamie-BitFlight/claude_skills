---
name: optimize
description: Use when writing delegation instructions to subagents, authoring CLAUDE.md files, rules, skills, or agent definitions, or auditing existing AI-facing content for bloat. Activates on "write a rule for", "add to CLAUDE.md", "create an agent", "update memory", or any request to author AI-facing instruction content. Removes discoverable data, explained-away knowledge, invented constraints, and stale cached facts.
user-invocable: true
---

# Writing Lean AI-Facing Instructions

The AI writing an instruction file and the AI reading it share the same training data and reasoning capability. Write only what that shared baseline cannot supply.

## Structural Principles

- **Decision tables over prose** — Avoid walls of text. Use decision tables and lookup structures for quick routing.
- **Positive framing** — Describe the right path to follow rather than just listing what not to do.
- **Checklists for validation** — Use checklists to enable explicit validation of the steps on the right path.
- **References extraction** — Heavy guidelines always go in `references/`. Keep the main skill and memory files lean with just routing logic and core principles.

## The Only Things Worth Writing

**User decisions** — choices the project made that differ from defaults: "We use pnpm, not npm." "Dark background, cream foreground."

**Project-specific facts** — paths, scripts, and tools that only exist here: "Run `node .claude/scripts/gh-api.cjs release latest <owner>/<repo>` to get the current major."

**Constraints** — things that would be done differently without this instruction: "Never copy a `uses:` version from another workflow file without verifying it."

**Mission-level anchoring** — This maintains alignment with the core purpose over time and provides a heuristic for decisions: "Does this change actually help achieve the mission of this system/task/product?" State the core principle (e.g., "all CI ops go through ci_monitor.py") and provide a routing table, rather than repeating granular details.

## What to keep external

**Discoverable data** — version numbers, hex codes, release tags, file listings, schema fields, or command `--help` outputs. If a command or lookup can produce it, don't store it. It will be wrong within days. Instead, verify that it is discoverable, and replace the prose with an instruction on **where** to discover the data and **when** to reach for which tool (e.g.,
"When doing A, B, or C then first read these references here: <path>").
For CLI tools, instruct the AI to discover arguments at runtime: "[ ] Run the command with `--help` and read CLI arguments before using it in a task."

**Explained knowledge** — step-by-step breakdowns of things Claude already knows how to do. It can be ambiguous whether something is a custom instruction set or just from training data. When optimizing a file, remove information generated from training data, as it will already be available for the other AI. Often, when writing documentation, the AI will waffle on and invent instructions just to get the document looking complete. These instructions often are never tested. A good way to see if something is slop is to follow the instructions or have a subagent follow them exactly, step by step, and find out if they work. This then provides a way to improve the instructions and update them if errors were found. If the instruction just explains how to do something standard, cut it.

**Invented constraints** — rules, fallback patterns, schemas that weren't requested and have no verified basis. Use a subagent or research it yourself to check if the constraint is based on a spec. If we generated the spec, evaluate whether the constraint helps achieve the product goal or if it is just noise. A common dangerous constraint added by AI is string length truncation (e.g., `head -50`, `tail -50`, array notation like `some_array[:50]`, or appending ellipses like `short part of the text ...`). This artificially hides information in a way that can't be tracked and leads to silent issues. If you can't cite the source or session that established a constraint, or if it's a dangerous truncation, cut it.

**Worked examples for obvious operations** — one example that shows a non-obvious pattern format is useful. Three examples walking through the same operation are not. Replace extra examples with: "See <url or reference file> for more examples."

**Duplicate content** — if it's in the skill, don't put it in the agent. If it's in the agent, don't put it in the rule. Pick the right place and put it there once. Use references: "Load `./references/{topic}.md` {when, before, to} {action, task, specialist knowledge req}"

## Where Each Type of Content Belongs

Read the reference for the content type you are writing or auditing:

- Writing or reviewing **CLAUDE.md or `.claude/rules/`** → `references/memory-and-rules.md`
- Writing or reviewing **SKILL.md or references/** → `references/skills.md`. Load [best-practices.md](../agentskills/references/best-practices.md) before writing reference pointers — it defines the correct `Load [file](./path)` format.
- Writing or reviewing **agent definition files** → `references/agents.md`

## Optimization Checklist

Execute this optimization surgically, making multiple passes. Use subagents to gather information, research, and validate instructions whenever possible.

- [ ] **Pass 0: Preparation**
  - [ ] Get the current word count and file size of the target file.
  - [ ] Take a backup of the file (either by committing it to git or creating a `*.bak` copy).
- [ ] **Pass 1: Mission & Structure**
  - [ ] Identify the core mission/purpose of the file.
  - [ ] Ensure the mission statement is explicitly anchored at the top.
  - [ ] Convert any long walls of prose into decision tables, lookup structures, or checklists.
- [ ] **Pass 2: Discoverable Data Extraction**
  - [ ] Scan for hardcoded versions, schema fields, or CLI flags.
  - [ ] Verify that this data is actually discoverable via terminal commands (e.g., `--help`) or specific URLs.
  - [ ] Replace the hardcoded data with routing logic: "When you need X, look in Y" or "[ ] Run `--help` before using."
- [ ] **Pass 3: Explained Knowledge & Constraints Audit**
  - [ ] Identify step-by-step tutorials for standard AI capabilities. Cut them and replace with references to authoritative sources.
  - [ ] Identify constraints and rules. Dispatch a subagent (or research yourself) to verify if they are based on a spec or if they are just AI-invented "slop" (like arbitrary string truncation).
  - [ ] Remove unverified or dangerous constraints.
- [ ] **Pass 4: Reference Extraction & Deduplication**
  - [ ] Move heavy guidelines, large examples, or deep context into `references/` files.
  - [ ] Check if the remaining content duplicates instructions found in other agents, skills, or rules.
  - [ ] Consolidate duplicated content into a single source of truth and use links/references elsewhere.
- [ ] **Pass 5: Validation & Review**
  - [ ] Have a subagent or yourself follow the newly optimized instructions step-by-step to ensure they still work and achieve the product goal without the removed bloat.
  - [ ] Compare the new file size and word count against the original.
  - [ ] Read the diff to identify if anything was hard-deleted that might have been overzealous.
  - [ ] Check with the user if the removal of any borderline content is desired before finalizing.
