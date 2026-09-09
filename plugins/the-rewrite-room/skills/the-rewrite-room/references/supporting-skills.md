# Optional Supporting Skills

Read this reference only for the `rwr:optimize` or `rwr:doc-to-skill` agent-facing workflow. Rewrite
Room's built-in writing contract remains the baseline when either optional skill is unavailable.

## Availability states

Record one state for each optional skill in the invoking leaf workflow's terminal report:

- `USED`: The skill was installed, activated, and applied to this result.
- `AVAILABLE`: The skill was installed, but its branch did not apply.
- `UNAVAILABLE`: An interactive request reached the missing skill branch; report its enhanced capability and offer installation once.
- `BUILTIN_ONLY`: A fixed prescribed task reached the missing skill branch; continue without pausing and apply Rewrite Room's built-in guidance.

When either state is `BUILTIN_ONLY`, state that the result used built-in guidelines only for that
capability. Missing optional support never blocks the baseline workflow.

## `writing-for-agents`

This skill adds the full information-hierarchy, invocation, pointer, completion, and pruning method
for agent-consumed documents. For optimization, activate it before building the whole-behavior
ledger. For conversion, activate it before classifying and designing the output skill.

Source: <https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-for-agents>

Installation options for an interactive request:

- Codex: offer `$skill-installer` for repository `mattpocock/skills`, path `skills/productivity/writing-for-agents`.
- Generic Agent Skills CLI: `npx skills add mattpocock/skills --skill writing-for-agents`.

## `skill-lapidary`

This skill adds a deeper conservation and reshape analysis across a complete Agent Skill, AGENTS.md,
CLAUDE.md, rules, prompt, or agent-definition boundary. When installed, activate it in analysis-only
mode with `--dry-run --grade reshape`, the original request, and the complete target. For conversion,
the complete target is the staged candidate directory after all planned files exist and before
promotion. Preserve the returned uncertainties, rejected changes, and conservation findings. Never
invoke `--apply` from Rewrite Room. Rewrite Room owns any later edit.

Source: <https://github.com/Jamie-BitFlight/skill-lapidary>

Installation options for an interactive request:

- Claude: `/plugin marketplace add Jamie-BitFlight/skill-lapidary`, then `/plugin install skill-lapidary@skill-lapidary`.
- Codex: `codex plugin marketplace add Jamie-BitFlight/skill-lapidary`, then `codex plugin add skill-lapidary@skill-lapidary`.

## Terminal support fields

Include these lines inside the invoking leaf workflow's terminal report. The leaf workflow owns the
`STATUS` field and uses only the status values defined in its own completion contract.

```text
SUPPORT:
  writing-for-agents: USED|AVAILABLE|UNAVAILABLE|BUILTIN_ONLY
  skill-lapidary: USED|AVAILABLE|UNAVAILABLE|BUILTIN_ONLY
GUIDANCE: enhanced|built-in-only
```
