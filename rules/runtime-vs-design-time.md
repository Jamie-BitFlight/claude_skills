# Runtime vs. Design-Time Audience and Environment

Every sentence in a skill, agent, command, `CLAUDE.md`/`AGENTS.md`, or plugin file has exactly one
of two audiences. Classify before writing or reviewing.

- **Runtime audience**: the agent executing the artifact, at the moment it does the task the
  artifact exists for. Runtime text tells it what to do, decide, resolve, or reason about.
- **Design-time audience**: whoever edits the artifact's source later — human or agent. Design-time
  text (comments, `MAINTENANCE.md`, ADRs, commit messages, PR descriptions) explains why the
  artifact is built the way it is. The executing agent never reads it.

Never write design-time content (history, past-tense rationale, "this fixes issue #N") into
runtime text. Never rely on runtime text to carry design-time-only facts — put those in a
maintenance file instead.

Design-time artifacts such as `SKILL-GOALS.md`, `BENCHMARKS.md`, `MAINTENANCE.md`,
`maintenance/*.md`, and `evals/**` travel inside the skill package but do not load with
`SKILL.md`. Do not link to them from runtime skill content. Maintenance, review, and evaluation
workflows may read them explicitly when making decisions about the skill. Put transient
provenance in a commit or PR and durable architectural decisions in an ADR.

## The environment split

The runtime audience does not run in the same place the artifact was authored. A skill, agent, or
`CLAUDE.md` file can be:

- copied into an unrelated project;
- loaded from a plugin installed in a repo that never had the plugin's source checked out;
- read by a subagent whose working directory is the consuming repo, not this one.

**Rule**: a fact, file path, or example in runtime text must resolve in every environment the
artifact can execute in — not just the one where it was authored. Before citing a path, command,
or example in runtime text, ask: "Does this exist for every agent that will load this artifact, or
only for one sitting in the authoring repo right now?"

- A path outside the artifact's own bundled files (its `references/`, `scripts/`, `assets/`) is
  runtime-safe only if it is guaranteed present in every consuming environment (a language
  stdlib path, a well-known config file name). A path into the authoring repo's own tree
  (`scripts/foo.py`, `plugins/other-plugin/...`) is not — an installed consumer never has that
  tree.
- If an example must live somewhere, put it inside the artifact's own bundled files (so it ships
  with the artifact) or inline it directly in the runtime text. Do not point at it by a bare path
  into the surrounding repo.
- A fact that is only true "in this repo" (a local convention, an internal script, a fixture file)
  is design-time knowledge about that repo, not a runtime instruction for a portable artifact —
  move it to that repo's own maintenance docs, or state it as a local convention rather than a
  universal instruction.

## Check before shipping

For every path, command, or fact in runtime text, confirm one of:

1. It is guaranteed present in any environment (stdlib, POSIX, a tool this artifact's own
   frontmatter/dependencies declare).
2. It is one of the artifact's own bundled files, referenced by a relative path inside the
   artifact's own directory.
3. It is inlined directly in the runtime text, needing no external lookup.

If none hold, delete it, inline it, or move it to the artifact's own bundled files — never leave a
runtime sentence pointing at something only the authoring repo has.
