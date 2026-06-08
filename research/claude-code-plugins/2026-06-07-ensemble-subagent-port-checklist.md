# Ensemble Subagent Port Checklist

Date: 2026-06-07

Source pattern:

- `plugins/plugin-creator/skills/ensemble-rule-review/SKILL.md`

## Purpose

Use a structured fan-out process for plugin research and migration so no single pass tries to hold:

- repo qualification
- concept mapping
- plugin classification
- runtime validation

all at once.

## Workstreams

### 1. Qualification worker

Input:

- one candidate repository

Output:

- exact star count
- does it contain `.claude-plugin/`?
- does it contain `.codex-plugin/`?
- is dual-target packaging real at plugin level?
- qualify / reject

### 2. Mapping worker

Input:

- one qualifying repository

Output:

- Claude manifest keys
- Codex manifest keys
- shared directories
- runtime-specific directories
- inferred migration rules
- unresolved ambiguity

### 3. Local plugin classifier

Input:

- one local plugin directory

Output:

- component inventory: skills / commands / agents / hooks / mcp
- migration class
- likely risk level
- recommended representative cohort

### 4. Runtime validation worker

Input:

- one Codex plugin already base-ported

Output:

- marketplace visible: pass/fail
- installable: pass/fail
- install succeeded: pass/fail
- visible in Codex session: pass/fail
- expected skill selected for representative prompt: pass/fail
- notes on missing behavior

## Required Output Schema

Every worker should emit:

```json
{
  "subject": "",
  "status": "pass|fail|mixed",
  "evidence": [],
  "findings": [],
  "gaps": [],
  "next_actions": []
}
```

## Guardrails

- do not count README mentions as structural evidence
- do not count repo root checks as sufficient for nested plugin collections
- do not mark a plugin as “ported” if only the manifest exists
- do not silently drop unsupported Claude behavior; record it explicitly
- separate `qualifying`, `nonqualifying but useful`, and `rejected/noisy`

## Ensemble Application To This Repo

Current recommended phase split:

1. qualification pass over reference repos
2. mapping extraction pass over qualifying repos
3. classification pass over local plugins
4. representative runtime validation pass
5. class-based migration rollout
