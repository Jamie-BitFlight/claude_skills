# Large File Write Strategy

## Scope

This policy applies to any agent that writes a document to the filesystem with a single `Write` call and may exceed **25,000 characters**. Treat 25K as this repo's conservative trigger for the strategies below.

It does not apply to output stored through an MCP operation. An agent that returns its result through a plan, task, or artifact operation writes no file, so no `Write` limit applies to it. Size limits on that path belong to the configured provider, are not 25K, and are not addressed here — check the provider before assuming one exists.

Determine which case applies by reading what the agent's dispatcher instructs it to call, not by the size of what it produces.

## Strategy A: Multi-File Split

Do not use Strategy A when a skill, agent, or dispatcher names one exact output path and declares
no split fallback for it. That path is a single-file contract — splitting it leaves its consumer
without the artifact it was promised. Use Strategy B for it.

When the contract itself declares a split fallback for the over-limit case (an index path plus
per-part files, used unless the caller explicitly requires a single file), follow that declared
fallback instead — it already specifies Strategy A's output shape and takes precedence over the
single-file default.

Otherwise split when the output has natural boundaries (sections, priorities, task groups, modules)
and consumers load the parts independently. Write an index file that references each part, and
write each part with its own `Write` call, each part under 25K characters.

## Strategy B: Skeleton + Edit-Fill

Use when the output must be a single file and exceeds 25K characters.

### Step 1: Plan document structure

List all sections, headers, and approximate content size per section. When the target document has
a required-sections contract defined elsewhere (a skill's SKILL.md, an agent's output spec), source
the list from that contract, not from what seems relevant — a self-invented list can silently omit
a required section. Confirm total exceeds 25K and no individual section exceeds 20K characters
(leave margin for Edit overhead).

### Step 2: Write skeleton

Issue a single `Write` call containing:

- YAML frontmatter (if applicable)
- All section headers in final order
- Placeholder stubs marking pending content

Target the skeleton at under 5K characters. Each placeholder uses the format:

```markdown
<!-- PENDING: Brief description of section content -->
```

### Step 3: Fill each section

Issue individual `Edit` calls, each replacing one placeholder stub with the full section content. Keep each Edit call under 20K characters. If a section exceeds 20K, split it into subsections with separate placeholders in Step 2.

### Step 4: Final verification

Read the completed file. Confirm:

- Zero `<!-- PENDING:` markers remain
- All planned sections contain content
- Document structure matches the Step 1 plan
- If a required-sections contract exists, every header it requires is present — not only the
  headers the skeleton happened to include
