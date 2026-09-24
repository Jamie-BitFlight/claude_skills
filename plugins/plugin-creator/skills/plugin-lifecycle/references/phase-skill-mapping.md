# Plugin Lifecycle Phase Mapping

Lookup reference for the owner and portable handoff at each phase.

| Phase | Owner | Handoff |
|---|---|---|
| 0: RT-ICA | inline procedure | See Phase 0 |
| 0.5: Discussion | lifecycle orchestrator | Write `discuss-CONTEXT.md` |
| 1: Assess | assessor skill | `/plugin-creator:assessor` |
| 2: Research | feature discovery skill | `/plugin-creator:feature-discovery` |
| 2: Research | three `plugin-creator:plugin-assessor` agents and one harness-native general-purpose agent | Dispatch together |
| 3: Design | RT-ICA skill | `/dh:rt-ica` |
| 4: Create skills | skill creator | `/plugin-creator:skill-creator` |
| 4: Create agents | agent creator | `/plugin-creator:agent-creator` |
| 4: Create hooks | hook creator | `/plugin-creator:hook-creator` |
| 5: Debug | lint skill | `/plugin-creator:lint` or `/plugin-creator:lint --fix PATH` |
| 5: Debug | refactor skill | `/plugin-creator:refactor-skill` |
| 6: Optimize goals | goal extractor | `/plugin-creator:skill-goal-extractor` |
| 6: Tighten | tightening skill | `/plugin-creator:evaluate-and-tighten-skills` |
| 6: Refactor plugin | refactor skill | `/plugin-creator:refactor-plugin` |
| 6: Optimize prose | Claude documentation optimizer | `/plugin-creator:optimize-claude-md` |
| 6: Audit skill | `plugin-creator:skill-auditor` | Dispatch agent |
| 6: Sync upstream docs | `plugin-creator:skill-content-updater` | Dispatch agent |
| 6: Optimize agent | methodology skill, then `plugin-creator:subagent-refactorer` | Activate `/plugin-creator:subagent-refactoring-methodology`, then dispatch agent |
| 6.5: Documentation | `plugin-creator:plugin-assessor` | Dispatch agent |
| 7: Verify | completion skill | `/plugin-creator:ensure-complete` |
| 7: Verify | skilllint | `uvx skilllint@latest check` |

Routing by concern:

- Establish a skill's goals before judging content: `/plugin-creator:skill-goal-extractor`.
- Remove content that serves no goal: `/plugin-creator:evaluate-and-tighten-skills`.
- Optimize surviving skill or Claude instructions through `/plugin-creator:optimize-claude-md`;
  that skill owns baselines, dispatch, independent verification, and reporting.
- Audit quality without writes by dispatching `plugin-creator:skill-auditor`.
- Sync against upstream documentation by dispatching `plugin-creator:skill-content-updater`.
- Rewrite only a description with `/plugin-creator:write-frontmatter-description`.
