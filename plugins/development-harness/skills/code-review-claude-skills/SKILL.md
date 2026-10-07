---
name: code-review-claude-skills
description: Reviews skill, agent, and plugin artifacts against their intended consumer's schema and runtime contract. Loaded by dh:code-reviewer for SKILL.md, agent definitions, or plugin manifests; checks discovery, frontmatter, triggers, tools, context cost, bundled references, and caller handoffs.
user-invocable: false
---

# Skill, Agent, and Plugin Review Patterns

Read [Review principles](../../docs/review-principles.md) before applying these checks; it defines
authority, applicability, evidence, and blocking criteria.

## Establish the Consumer

Identify whether the artifact targets a portable skill package, a host-specific skill, a
project/user agent, a plugin agent, or a plugin manifest. Read its declared destinations and the
target's active validator configuration. Do not apply one artifact type's frontmatter or discovery
rules to another.

When available, load the matching policy reference: `/plugin-creator:agentskills` for the portable
format, `/plugin-creator:claude-skills-overview-2026` for Claude skills,
`/plugin-creator:claude-subagent-reference` for Claude agents, or
`/plugin-creator:claude-plugins-reference-2026` for plugin manifests. These references own the
destination-specific field rules. If unavailable, use the target consumer's official schema or
configured validator and the checks below; report any unresolved capability as unvalidated.

## Frontmatter and Discovery

- Parse frontmatter and verify required fields, value types, names, lengths, and identity resolution against the selected destination. Do not invent a universal name grammar, directory-name equality rule, or scalar/list representation.
- Check that descriptions identify the actual capability and activation conditions. A parsed but misleading description can route the wrong task or hide the intended skill.
- Verify that tool, model, permission, and invocation fields are supported and effective for this artifact's destination. Distinguish skill metadata from agent metadata and plugin restrictions from project/user behavior.
- Check configured model values against the selected host/provider contract; do not reject a full identifier solely because a tier alias is preferred elsewhere.
- Run the applicable validator in read-only mode when available. Do not run `--fix`, change frontmatter, or update generated state while reviewing the target.

## Description Quality

- Front-load discriminating trigger conditions and the outcome; check the applicable description budget rather than assuming one host's limit applies everywhere.
- Verify that described inputs, outputs, and side effects match the body and callable resources.
- Use direct third-person activation guidance. Report vague wording with the concrete routing ambiguity it creates, rather than requiring one stock opening phrase.

## Context Cost

- Apply the target's actual metadata/body budget and enforced authoring gates. Report exclusions or truncation with evidence; do not turn an invented token threshold into a blocking rule.
- Identify redundant instructions, repeated shared policy, or inline resources that increase reading cost without changing decisions. Preserve domain knowledge and constraints the consuming agent needs.
- Prefer focused examples and conditional references for detail that only some tasks require. Check that every disclosed reference states what it contains and when to read it.

## Tools and Invocation

- Match available operations to the agent's responsibility and the host's actual enforcement semantics. A named tool field is not evidence that the host enforces the intended restriction.
- Preserve read-only review of the target. Distinguish target mutation from separately authorized artifact, memory, or disposable-experiment writes; a `Write` capability alone does not establish that the reviewer edits the target.
- Inspect shell and tool calls for consequential effects and authorization; removing an edit tool alone does not make an unrestricted shell read-only.
- Check user/model invocation controls against the intended activation path. Do not disable model invocation merely because a skill contains a shell command; establish whether the command can execute automatically and what authorization its effects need.
- Confirm that dependencies intended for preloading or runtime activation are available under the destination's rules; report unavailable required knowledge and the affected handoff.

## Agent Contracts

- Trace what the caller supplies and consumes: task, evidence, artifact reference, verdict, and terminal status where present.
- Apply `STATUS: DONE` / `STATUS: BLOCKED`, `ARTIFACTS`, and `NEEDED` requirements when the caller defines that protocol. Do not impose DH's envelope on an unrelated agent with another supported contract.
- Check that missing inputs, partial evidence, failures, and completion are distinguishable to the caller. Uncertainty must not become a fabricated result; block only the work whose required contract cannot be satisfied.
- Verify that the final response or registered artifact actually returns the evidence the caller needs; instructions to write a report are not evidence it was delivered.

## References and Runtime Resources

- Resolve bundled links from the containing artifact inside the installed plugin boundary. Shared plugin-root `docs/` content is valid when shipped and reachable; a repository-only path outside that boundary is not an installed dependency.
- Use annotated Markdown links for bundled references and activation notation for optional cross-plugin capabilities. Do not traverse to a sibling plugin's checkout or depend on an author-only absolute path.
- Verify any substituted path variable against the actual host; a variable that remains literal is not a resolved resource.
- Check referenced scripts, assets, schemas, and instructions exist and their inputs/outputs agree with the caller. Preserve a useful fallback when an optional external plugin is absent.
- Apply the project's code-fence and nesting conventions so examples remain parseable; diagnose malformed structure instead of classifying every presentation preference as a runtime defect.

## Plugin Manifests

- Check component paths and installed discovery against the manifest consumer's specification. Distinguish default discovery, additional locations, and replacement lists per component category.
- Verify every required skill, agent, command, hook, or server remains reachable after a manifest change. A syntactically valid manifest can still omit an intended component.
- Confirm referenced components stay inside the distributed plugin and use the correct namespace at their call sites.

## Discriminating Examples

| Candidate concern | Evidence that changes the decision |
| --- | --- |
| A skill links to `../../docs/review-principles.md` | Resolve it inside the installed plugin and verify the file is shipped; the directory name `docs` is not a defect. |
| A reviewer has a write tool for a registered report | Check its authorized output destination and whether reviewed files remain unchanged; investigate actual target-mutation authority. |
| An agent uses a model ID or a YAML tool list | Validate the selected consumer's accepted fields and representations; a different preferred spelling is not evidence of rejection. |
| A skill names an optional cross-plugin policy | Check availability and its declared fallback; do not infer installation from the author's repository layout. |
