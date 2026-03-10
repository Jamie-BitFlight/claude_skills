---
name: plugin-creator workflow skill — step-by-step orchestration of assess, research, design, debug, create, optimize, and verify phases
description: 'The plugin-creator plugin lacks a unified workflow skill that guides users through the full plugin lifecycle in the correct sequence. Currently, individual skills and agents exist (assessor, skill-creator, agent-creator, refactor-plugin, etc.) but there is no single entry point that chains them together with the right handoffs, decision gates, and phase transitions. Users and orchestrators must know which skill to invoke at each phase, what artifacts each phase produces, and what conditions trigger moving to the next phase. Success looks like: a single /plugin-creator:plugin-lifecycle (or similar) skill that defines the ordered phases, names the correct skill/agent for each phase, specifies the input artifacts and output artifacts per phase, includes decision gates (e.g., skip research if plugin already exists, skip debug if no errors), and handles the full lifecycle from blank canvas to marketplace-ready plugin. The skill is working when an orchestrator can follow it end-to-end and produce a validated, linted plugin without needing to know the plugin-creator internals.'
metadata:
  topic: plugin-creator-workflow-skill-step-by-step-orchestration-of-
  source: User request
  added: '2026-03-02'
  priority: completed
  type: Feature
  status: done
  issue: '#427'
  last_synced: '2026-03-03T14:07:09Z'
  groomed: '2026-03-03'
---

## Groomed (2026-03-03)

### Issue Classification

**Type**: unbounded-design
**Rationale**: New capability with open solution space; no traceable failure, no prior recurrence. Phase sequence, gate conditions, and artifact schema must be designed from scratch.
**Analysis Method**: design-framing
**Scenario Target**: Orchestrator/user building a plugin from scratch → follows a single skill end-to-end without knowing plugin-creator internals

