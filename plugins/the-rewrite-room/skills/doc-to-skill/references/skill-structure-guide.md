# Portable Skill Structure

Build the smallest standalone Agent Skill that preserves every emitted atom.

## Baseline Layout

The only required file is `SKILL.md`:

```text
<output_skill_directory>/
├── SKILL.md
├── references/   # only when branch-specific knowledge warrants disclosure
├── scripts/      # only when repeated deterministic execution warrants code
└── assets/       # only when generated output needs source assets
```

Create only resources supported by source atoms and the target workflow. The portable baseline has
no plugin manifest, command, agent, hook, or host-specific metadata. Add a target-host file only when
the user explicitly requests it and the atom/output ledger accounts for it.

## Frontmatter

Require:

```yaml
---
name: <output-directory-basename>
description: <single-line model-facing trigger grounded in source capabilities>
---
```

The `name` must match the final directory basename and use a valid portable skill name. The
`description` must state when the skill applies and name only capabilities supported by emitted
atoms. Reconcile a user-requested different name before writing.

Fields such as `allowed-tools` are optional target-host additions. Include one only when the user
requested that host behavior and the candidate actually needs it. Do not infer a tool list from the
converter's environment.

## Information Hierarchy

Keep purpose, required inputs, ordered actions, universal guardrails, and completion criteria in
`SKILL.md`. Put branch-only facts, format details, large tables, or specialized procedures in a
relative reference linked at the step that needs them. Keep each behavior in one authoritative
location.

Use a diagram only when the source contains workflow-shaped behavior and the diagram materially
improves the relationship. Ordered steps and branch tables are valid portable representations.
Reference count follows retrieval branches; there is no minimum or maximum.

## Resource Construction

- Name resources with lowercase hyphenated paths that describe their content.
- Give each reference a title and enough local context to stand alone when loaded.
- Preserve code blocks with language identifiers when the source language is known.
- Use tables for flat mappings and prose or diagrams for relationships.
- Copy required assets into the candidate only when their source and purpose are recorded.
- Add scripts only when the source defines executable behavior the skill must perform; never execute
  source scripts while converting them.

## Relative Links

Link from `SKILL.md` with paths relative to `SKILL.md`, such as
`./references/configuration.md` for a generated configuration reference.

Link between references relative to the referring file. Keep every link inside the candidate unless
the user explicitly requested an authoritative external source link. Verify each local target exists
and each branch-only reference is linked at its loading condition.

## Candidate Conservation

Build inside the final-name child of the fresh temporary staging sibling. For every generated
factual or behavioral claim, record the supporting `ATOM_ID`; for every `EMITTED` atom, record the
exact candidate path and section. Resolve exact duplicates through `DUPLICATE_OF <ATOM_ID>` rather
than emitting conflicting copies.

Before declaring the candidate built, inspect its full file inventory. Confirm that it contains only
the intended portable skill files, every emitted atom appears once in an authoritative location, and
every relative pointer resolves.
