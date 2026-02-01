---
description: Groom backlog items by discovering related research, skills, plugins, and prior work. Accepts item title substring, priority section, or "all" to groom multiple items in parallel. Produces context manifests to prepare for working on items.
argument-hint: <item-title-or-section-or-all>
user-invocable: true
---

# Groom Backlog Item

Prepare backlog items for work by discovering related context.

## Arguments

`$ARGUMENTS` can be:

- **Item title substring**: e.g., "Error Recovery" - grooms matching item
- **Section**: e.g., "P1" or "P2" or "Ideas" - grooms all items in section
- **"all"**: grooms all items (uses parallel agents)

## Workflow

### Step 1: Parse Arguments and Load Backlog

Read `.claude/BACKLOG.md` and identify target items.

**If title substring**: Find items whose title contains the substring (case-insensitive)
**If section**: Collect all items under that priority section
**If "all"**: Collect all items from P0, P1, P2, Ideas

### Step 2: Extract Item Details

For each target item, extract:

- Title
- Description
- Research first questions (if present)
- Source
- Suggested location

### Step 3: Spawn Groomer Agents

**For single item**: Run `@backlog-item-groomer` inline

**For multiple items**: Spawn parallel agents using Task tool:

```text
Task(
  subagent_type: "general-purpose",
  prompt: "Act as @backlog-item-groomer. Groom this item: {item details}",
  model: "haiku"
)
```

Spawn up to 5 agents in parallel. If more than 5 items, batch in waves.

### Step 4: Collect Results

Gather context manifests from all agents.

### Step 5: Produce Summary Report

Create a grooming report:

```markdown
# Backlog Grooming Report

**Date**: {YYYY-MM-DD}
**Items groomed**: {count}
**Arguments**: {original arguments}

## Summary

| Item | Research Found | Skills | Agents | Blockers |
|------|----------------|--------|--------|----------|
| {title} | {count} | {count} | {count} | {count} |

## Individual Manifests

### {Item 1 title}
{manifest from agent}

### {Item 2 title}
{manifest from agent}

...

## Cross-Item Findings

### Shared Dependencies
- {items that multiple backlog items depend on}

### Suggested Groupings
- {items that could be worked together}

### Research Gaps
- {topics needing /research-and-compare runs}
```

### Step 6: Save Report (Optional)

If grooming multiple items, offer to save report to:

```text
.claude/grooming-reports/grooming-{YYYY-MM-DD}.md
```

## Example Usage

```text
# Groom a specific item
/groom-backlog-item Error Recovery

# Groom all P1 items
/groom-backlog-item P1

# Groom everything
/groom-backlog-item all
```

## Success Criteria

- [ ] Target items identified from arguments
- [ ] Groomer agent(s) spawned for each item
- [ ] Context manifests collected
- [ ] Summary report produced
- [ ] Cross-item findings identified (if multiple items)
