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
| 6: Optimize | `/plugin-creator:skill-goal-extractor` | `Skill(skill="plugin-creator:skill-goal-extractor")` |
| 6: Optimize | `/plugin-creator:evaluate-and-tighten-skills` | `Skill(skill="plugin-creator:evaluate-and-tighten-skills")` |
| 6: Optimize | `/plugin-creator:refactor-plugin` | `Skill(skill="plugin-creator:refactor-plugin")` |
| 6: Optimize | `@ai-doc-optimizer` | subagent_type="plugin-creator:ai-doc-optimizer" |
| 6: Optimize | `@skill-auditor` | subagent_type="plugin-creator:skill-auditor" |
| 6: Optimize | `@skill-content-updater` | subagent_type="plugin-creator:skill-content-updater" |
| 6: Optimize | `@subagent-refactorer` | subagent_type="plugin-creator:subagent-refactorer" |

Routing by concern:
- Establish what a skill exists to achieve, before judging any of its content → `/plugin-creator:skill-goal-extractor` skill
- Remove content that serves no goal (decides whether text exists) → `/plugin-creator:evaluate-and-tighten-skills` skill, run before optimizing
- Optimize existing content (decides how surviving text reads — clarity, structure, Anthropic prompt engineering principles) → `ai-doc-optimizer` agent (subagent_type="plugin-creator:ai-doc-optimizer")
- Audit quality (read-only, no writes, score against completeness categories) → `skill-auditor` agent (uses `/plugin-creator:audit-skill-completeness`)
- Sync content against upstream docs (add NEW/fix STALE from live sources) → `skill-content-updater` agent (subagent_type="plugin-creator:skill-content-updater")
- Write/rewrite description field only → `/plugin-creator:write-frontmatter-description` skill directly
| 6.5: Documentation | `@plugin-assessor` | subagent_type="plugin-creator:plugin-assessor" |
| 7: Verify | `/plugin-creator:ensure-complete` | `Skill(skill="plugin-creator:ensure-complete")` |
| 7: Verify | `skilllint` | `uvx skilllint@latest check` |
