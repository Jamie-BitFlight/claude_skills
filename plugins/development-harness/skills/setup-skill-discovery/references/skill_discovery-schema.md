# skill_discovery.yaml — Schema Reference

This document is the canonical definition of every field in `.dh/skill_discovery.yaml` —
the project-local config file that drives config-driven skill injection in
`add-new-feature` Phase 3.

---

## File Location

```
<project-root>/.dh/skill_discovery.yaml
```

This is a Tier 1 path — commit it to git. It is project-local and intentionally
version-controlled alongside other `.dh/` planning artifacts.

---

## Top-Level Fields

Five top-level fields are defined. Unknown top-level keys are silently ignored
for forward compatibility.

---

### `skill_discovery`

| Property | Value |
|---|---|
| **Type** | string enum |
| **Allowed values** | `auto`, `suggest`, `off` |
| **Default** | `auto` |
| **Required** | No |

**Description**: Controls the injection gate mode for Phase 3.

| Mode | Behaviour |
|---|---|
| `auto` | Collect `always_use_skills` + evaluate `skill_rules`. Inject matched skills into the architect delegation prompt. |
| `suggest` | Emit a note listing candidate skills. Set `domain_skills = []`. Continue non-blocking — no injection. |
| `off` | Skip all skill discovery. `domain_skills = []`. No note emitted. |

**Validation**: Value MUST be one of `auto`, `suggest`, or `off` (case-sensitive). Any other
value is malformed and causes Phase 3 to treat the file as empty.

**Example**:

```yaml
skill_discovery: auto
```

---

### `always_use_skills`

| Property | Value |
|---|---|
| **Type** | sequence of strings |
| **Default** | `[]` (empty list) |
| **Required** | No |

**Description**: Skills injected unconditionally into every `add-new-feature` run, regardless
of the feature request content or any `skill_rules` evaluation. Use for project-wide
conventions that apply to every feature — for example, a project-specific code-review skill
or a conventions reference that every architect run should include.

Recommended: 0–2 entries. More than 2 unconditional skills bloat every architect prompt.

**Validation**:
- Value MUST be a YAML sequence (list), not a scalar or mapping.
- Each element MUST be a string in `provider:skill-name` format (colon-separated, no spaces).
- An empty list (`[]` or omitted) is valid.
- Skills listed here are NEVER filtered out by `avoid_skills` — the unconditional contract is absolute.

**Example**:

```yaml
always_use_skills:
  - plugin-creator:claude-skills-overview-2026   # every feature needs skill format awareness
```

---

### `skill_rules`

| Property | Value |
|---|---|
| **Type** | sequence of objects |
| **Default** | `[]` (empty list) |
| **Required** | No |

**Description**: Conditional skill injection rules. Each entry defines a natural-language
`when` condition and a `use` list of skills to inject when that condition is satisfied.
The orchestrating agent evaluates each `when` condition using LLM reasoning against the
current feature request context (see **`when` Evaluation Semantics** below).

**Object structure** (each entry):

| Sub-field | Type | Required | Description |
|---|---|---|---|
| `when` | string | Yes | Natural-language condition evaluated against the feature request |
| `use` | sequence of strings | Yes | Skills to inject when the condition is satisfied |

**Validation**:
- The top-level value MUST be a YAML sequence (list), not a scalar or mapping.
- Each entry MUST be a YAML mapping containing at least the `when` and `use` keys.
- An entry missing the `use` key is malformed — Phase 3 treats the entire file as empty.
- `use` MUST be a YAML sequence. A scalar `use` is malformed.
- `when` MUST be a non-empty string.
- Each element of `use` MUST be a string in `provider:skill-name` format.
- An empty list (`[]` or omitted) is valid.

**Example**:

```yaml
skill_rules:
  - when: "feature request involves hooks, PreToolUse, PostToolUse, or event-driven plugin behaviour"
    use:
      - plugin-creator:hooks-guide
      - plugin-creator:hook-creator

  - when: "project has TypeScript files and the feature touches the API layer or route handlers"
    use:
      - plugin-creator:mcp-integration
```

#### `when` Evaluation Semantics — LLM Reasoning

The `when` field is a natural-language condition. Phase 3 evaluates it using **LLM reasoning**,
not keyword or substring matching.

**How evaluation works**: The orchestrating agent reads the `when` condition and the current
feature request (title + description + detected stack). It applies semantic judgment to
determine whether the condition is unambiguously satisfied by the feature context.

- A rule fires when the condition is **clearly and unambiguously satisfied**.
- A rule does **not** fire when the connection is speculative, tangential, or uncertain.
- The agent does not fire rules speculatively — uncertainty means no-fire.

**Mandatory examples**:

| `when` condition | Feature request | Fires? | Reason |
|---|---|---|---|
| `"feature request involves hooks or PreToolUse"` | "Add a PreToolUse hook to validate Bash commands before execution" | Yes | Feature explicitly involves hooks and PreToolUse |
| `"feature request involves hooks or PreToolUse"` | "Add dark mode toggle to the dashboard" | No | No connection to hooks or PreToolUse |
| `"project has TypeScript files and the feature touches the API layer"` | "Add a new REST endpoint for job status polling" | Yes | Condition is satisfied: TS project + API layer |
| `"project has TypeScript files and the feature touches the API layer"` | "Fix typo in README" | No | Does not touch API layer |

**What makes a good `when` condition**:
- Describes a clear, observable scenario using natural language
- Names specific technologies, file types, patterns, or domains
- Can be evaluated without ambiguity against a feature description

**What makes a poor `when` condition**:
- Vague: `"when code changes are made"` — always true
- Overly narrow: `"when function add_user is modified"` — too brittle
- Boolean logic chains longer than two clauses — prefer two separate rules

---

### `prefer_skills`

| Property | Value |
|---|---|
| **Type** | sequence of strings |
| **Default** | `[]` (empty list) |
| **Required** | No |

**Description**: Lower-priority skill suggestions. These are advisory hints, not injected
unconditionally. Phase 3 may surface them as suggestions when `skill_discovery: suggest` is
active or when no `skill_rules` entries fire. They serve as tiebreakers or fallback candidates
when the agent is choosing among alternatives.

`prefer_skills` entries are NOT added to `domain_skills` in `auto` mode unless a `skill_rules`
rule fires that includes them. They do not bypass the `when` evaluation step.

**Validation**:
- Value MUST be a YAML sequence (list), not a scalar or mapping.
- Each element MUST be a string in `provider:skill-name` format.
- An empty list (`[]` or omitted) is valid.
- Entries in `prefer_skills` ARE filtered by `avoid_skills` (unlike `always_use_skills`).

**Example**:

```yaml
prefer_skills:
  - holistic-linting:holistic-linting   # useful if brought up, but not every feature needs it
```

---

### `avoid_skills`

| Property | Value |
|---|---|
| **Type** | sequence of strings |
| **Default** | `[]` (empty list) |
| **Required** | No |

**Description**: Skills to never inject, regardless of `skill_rules` or `prefer_skills`
evaluation. Use to suppress skills that conflict with project conventions, are superseded by
a project-specific version, or are known to produce wrong output for this codebase.

**Validation**:
- Value MUST be a YAML sequence (list), not a scalar or mapping.
- Each element MUST be a string in `provider:skill-name` format.
- An empty list (`[]` or omitted) is valid.

**Example**:

```yaml
avoid_skills:
  - python-engineering:python3-stdlib-only   # this project uses third-party libs; stdlib-only is wrong
```

---

## Field Interaction Rules

### `avoid_skills` overrides `prefer_skills`

If a skill appears in both `prefer_skills` and `avoid_skills`, it is excluded. `avoid_skills`
always wins.

### `always_use_skills` is never filtered by `avoid_skills`

Skills in `always_use_skills` are injected unconditionally. They bypass `avoid_skills`.
If you want to suppress an unconditional skill, remove it from `always_use_skills` directly —
adding it to `avoid_skills` has no effect on it.

### `skill_rules` entries are filtered by `avoid_skills`

When a `skill_rules` entry fires, its `use` list is assembled. Then any skills in
`avoid_skills` are removed from that assembled list before injection. If all skills in a
fired rule are in `avoid_skills`, that rule contributes nothing to `domain_skills`.

### Injection assembly order

Phase 3 assembles `domain_skills` in this order:
1. Add all `always_use_skills`
2. Evaluate each `skill_rules` entry; add `use` skills for all firing rules
3. Remove any skills in `avoid_skills` (does not affect `always_use_skills`)
4. De-duplicate (preserve first-occurrence order)

`prefer_skills` does not affect `domain_skills` in `auto` mode unless surfaced by a
firing rule that explicitly references them.

---

## Validation Rules — Malformed vs Valid

### Malformed (Phase 3 treats file as empty, emits a warning)

- Invalid YAML syntax (cannot parse)
- `skill_discovery` value is not one of `auto`, `suggest`, `off`
- Any list field (`always_use_skills`, `prefer_skills`, `avoid_skills`, `skill_rules`) is not a YAML sequence
- Any `skill_rules` entry is missing the `use` key
- Any `use` value is not a YAML sequence

### Valid (no error, normal processing)

- Empty file — all fields take their defaults (`skill_discovery: auto`, all lists empty)
- Unknown top-level keys — silently ignored
- Empty lists for any field
- `skill_rules` with zero entries

---

## Examples

### Minimal Valid File

The smallest valid `skill_discovery.yaml` — an empty file with defaults applied:

```yaml
# .dh/skill_discovery.yaml
# (empty — all defaults apply)
```

Or equivalently, with explicit defaults:

```yaml
skill_discovery: auto
always_use_skills: []
prefer_skills: []
avoid_skills: []
skill_rules: []
```

Both are valid. Phase 3 treats them identically: `skill_discovery` is `auto`, all lists
empty, `domain_skills = []`.

---

### Complete Annotated Example

A realistic `skill_discovery.yaml` for a Claude Code plugin project:

```yaml
# .dh/skill_discovery.yaml
# Config-driven skill injection for add-new-feature Phase 3.
# Generated by /dh:setup-skill-discovery — review and adjust as needed.

skill_discovery: auto   # auto | suggest | off

# Skills injected unconditionally on every add-new-feature run.
# Recommended: 0-2 entries.
always_use_skills:
  - plugin-creator:claude-skills-overview-2026   # ensures skill format awareness on all features

# Tiebreaker advisory — not added unconditionally; may surface in suggest mode.
prefer_skills:
  - holistic-linting:holistic-linting

# Never inject these, regardless of skill_rules evaluation.
avoid_skills:
  - python-engineering:python3-stdlib-only       # this project uses third-party deps

# Conditional rules: each 'when' is evaluated via LLM reasoning against the feature request.
skill_rules:

  - when: "feature involves hooks, PreToolUse, PostToolUse, or plugin event lifecycle"
    use:
      - plugin-creator:hooks-guide
      - plugin-creator:hook-creator

  - when: "feature involves creating or modifying a SKILL.md, agent definition, or plugin component"
    use:
      - plugin-creator:plugin-creator
      - plugin-creator:agent-creator

  - when: "feature involves MCP server tools, tool registration, or FastMCP patterns"
    use:
      - fastmcp-creator:fastmcp-creator

  - when: "feature involves Python source files, pytest tests, or pyproject.toml changes"
    use:
      - python-engineering:python3-core
      - python-engineering:python3-testing

  - when: "feature touches dashboard React components, UI layout, or frontend behaviour"
    use:
      - plugin-creator:component-patterns
```

---

## Skill Identifier Format

All skill references in `skill_discovery.yaml` MUST use the `provider:skill-name` format:

```
provider:skill-name
```

- `provider` — the plugin or namespace prefix (e.g., `plugin-creator`, `python-engineering`)
- `skill-name` — the skill's directory name (lowercase, hyphens, no spaces)
- Separator — a single colon (`:`)

**Valid**: `plugin-creator:hooks-guide`, `python-engineering:python3-core`, `dh:add-new-feature`

**Invalid**: `plugin-creator/hooks-guide` (slash), `hooks-guide` (no provider), `plugin-creator:Hooks-Guide` (uppercase)

Phase 3 passes these identifiers directly to `Skill(skill="...")`. A skill that cannot be
found causes Claude Code to emit a skill-not-found warning; it does not abort the run.
