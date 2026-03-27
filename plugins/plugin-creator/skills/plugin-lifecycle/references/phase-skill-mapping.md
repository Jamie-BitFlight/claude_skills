# Plugin Lifecycle — Phase-to-Skill Mapping

Lookup reference: which skill or agent handles each phase, and the exact invocation syntax.

| Phase | Skill/Agent | Invocation |
|-------|-------------|------------|
| 0: RT-ICA | `rt-ica` skill (inline procedure) | Inline — see Phase 0 |
| 0.5: Discussion | Direct — capture to discuss-CONTEXT.md | Inline — see Phase 0.5 |
| 1: Assess | `/plugin-creator:assessor` | `Skill(skill="plugin-creator:assessor")` |
| 2: Research | `/plugin-creator:feature-discovery` | `Skill(skill="plugin-creator:feature-discovery")` |
| 2: Research | 4-way parallel researchers | subagent_type="plugin-creator:plugin-assessor" x3 + "general-purpose" x1 |
| 3: Design | `/dh:rt-ica` | `Skill(skill="dh:rt-ica")` |
| 4: Create | `/plugin-creator:skill-creator` | `Skill(skill="plugin-creator:skill-creator")` |
| 4: Create | `/plugin-creator:agent-creator` | `Skill(skill="plugin-creator:agent-creator")` |
| 4: Create | `/plugin-creator:hook-creator` | `Skill(skill="plugin-creator:hook-creator")` |
| 5: Debug | `/plugin-creator:lint` | `Skill(skill="plugin-creator:lint")` |
| 5: Debug | `/plugin-creator:refactor-skill` | `Skill(skill="plugin-creator:refactor-skill")` |
| 5: Debug | `/plugin-creator:lint` | `Skill(skill="plugin-creator:lint", args="--fix PATH")` |
| 6: Optimize | `/plugin-creator:refactor-plugin` | `Skill(skill="plugin-creator:refactor-plugin")` |
| 6: Optimize | `@contextual-ai-documentation-optimizer` | subagent_type="plugin-creator:contextual-ai-documentation-optimizer" |
| 6: Optimize | `@subagent-refactorer` | subagent_type="plugin-creator:subagent-refactorer" |
| 6.5: Documentation | `@plugin-assessor` | subagent_type="plugin-creator:plugin-assessor" |
| 7: Verify | `/plugin-creator:ensure-complete` | `Skill(skill="plugin-creator:ensure-complete")` |
| 7: Verify | `skilllint` | `uvx skilllint@latest check` |
