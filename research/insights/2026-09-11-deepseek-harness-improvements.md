# Improvement Proposals: DeepSeek Harness

**Research entry**: ./research/agent-frameworks/deepseek-harness.md
**Generated**: 2026-09-11
**Patterns assessed**: 8
**Backlog items created**: 3 (stored locally; GitHub issue creation returned 403 — GraphQL is unavailable from this session, so no issue numbers were assigned and each item needs a `backlog_sync` from a session that can reach the REST API)
**Deferred (low confidence)**: 3
**Skipped (already covered or incompatible)**: 2

---

## Improvement 1: plugin-settings has no criterion for which values must become settings

**Source pattern**: "No hardcoded tunables in plugins: deployment-varying choices are validated `Config` fields changeable from cordis.yml; a `DEFAULT_*` constant or test hook is not configurability" — Installation & Usage → Configuration (deepseek-harness.md line 161, quoting the upstream AGENTS.md).
**Local system**: `plugins/plugin-creator/skills/plugin-settings/SKILL.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: created as `p1-plugin-settings-skill-has-no-criterion-for-which-values-must` (no issue number — GitHub issue creation returned 403)

### Current state

The skill's "When to Use This Pattern" decision tree (lines 13-25) begins at `"Plugin needs user-configurable behavior"` and branches only on *kind of state* — per-project configuration, agent coordination state, hook activation control, loop iteration state. Every branch presumes the decision that a value should be configurable has already been made elsewhere.

"Best Practices" (lines 167-206) covers defaults when the file is absent, field validation, atomic updates, and the restart requirement — all of which describe how to *read* a setting that already exists. Nothing in the file states which values must become settings fields in the first place, and nothing states the negative case: that a constant carrying a default, or an override that only tests use, is not configurability.

### Target state

`plugin-settings/SKILL.md` carries a classification step ahead of the existing state-kind branch: a value that varies by project, machine, or environment is deployment-varying and belongs in the settings frontmatter; a value fixed by the plugin's design stays a constant. The negative case is stated explicitly — a `DEFAULT_*`-style constant inside a hook or script, or a test-only override hook, does not satisfy the requirement.

### Measurable signal

- `grep -n "deployment-varying" plugins/plugin-creator/skills/plugin-settings/SKILL.md` returns at least one match.
- The "When to Use This Pattern" mermaid has a decision node that asks whether the value varies by deployment *before* branching on state kind.
- Running `/plugin-creator:plugin-settings` against a hook script containing a hardcoded numeric threshold produces a statement naming that threshold as deployment-varying and directing it into frontmatter, rather than only explaining how to parse frontmatter.

---

## Improvement 2: no rule bounds runtime validation to trust boundaries

**Source pattern**: "Trust TypeScript at typed same-process boundaries. Do not add runtime validation, fallback behavior, or hostile-input tests solely for values the static interface requires" — Technical Architecture → Type System and TypeScript at Scale (deepseek-harness.md line 117, quoting the upstream AGENTS.md).
**Local system**: `rules/exception-handling.md`, `rules/silent-failure-prevention.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: created as `p1-no-rule-bounds-runtime-validation-to-trust-boundaries-so-sil` (no issue number — GitHub issue creation returned 403)

### Current state

`rules/exception-handling.md` (26 lines) addresses one defensive anti-pattern only — broad `except Exception` catches — and explicitly names its training-data origin. It says nothing about redundant type or value guards.

`rules/silent-failure-prevention.md` lines 40-66 ("Branching on Input Values Requires an Explicit Fallback") requires every `if`/`elif` chain or match "on an input value" to end in a branch that acts or raises. The rule never defines which inputs it means. Read literally at a same-process call whose parameters are annotated (and, per `AGENTS.md` Code Conventions, increasingly Pydantic `BaseModel` fields), it mandates fallback branches for states the static interface already excludes.

A grep of `rules/` and `docs/` for `defensive|trust the type|isinstance check|redundant validation|already guarantee` returns a single hit — `docs/dh-backend-beads/comparison-research/07-skills-hooks-beads-integration.md` line 406, a one-off case note proposing a defensive widening, not a rule. No rule file in the repo bounds where validation belongs.

### Target state

A rule states that runtime validation, fallback branches, and hostile-input tests belong at trust boundaries — parsed JSON/YAML, CLI arguments, subprocess output, network and MCP payloads, filesystem content — and not at same-process calls whose parameter types the annotations or Pydantic models already guarantee. `rules/silent-failure-prevention.md`'s "input value" wording points at that boundary definition so the two rules cannot be read as requiring guards on internal typed calls.

### Measurable signal

- `grep -rn "trust boundary" rules/` returns at least one match in a rule file.
- The "Branching on Input Values Requires an Explicit Fallback" section in `rules/silent-failure-prevention.md` names which inputs the requirement covers.
- A reviewer rejecting an `isinstance()` guard (or a `None` fallback) on a parameter that is annotated and called only in-process can cite a rule file path for the rejection.

---

## Improvement 3: component selection terminates at one component, with no capability-completeness check

**Source pattern**: "A capability seam comprises Service Definition / Service Provider / Consumer roles. It is complete, never one role; split only when roles evolve independently" and "Extension plugins depend on Service Definitions, never concrete providers" — Technical Architecture → Capability Seam Pattern (deepseek-harness.md lines 89-97).
**Local system**: `plugins/plugin-creator/skills/component-patterns/SKILL.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: created as `p1-component-patterns-selection-tree-terminates-at-one-componen` (no issue number — GitHub issue creation returned 403)

### Current state

The Component Selection Framework (lines 42-59) is a single-exit decision tree: each leaf names exactly one component type and one creator skill — Hook, MCP Server, Agent, Skill, or legacy Command. The Quick Reference (lines 63-82) reinforces the exclusive framing by listing each type's differentiators side by side.

"Cross-Component Patterns" (lines 136-199) covers shared `lib/` code, layered directories, and modular extensions — how files are organized, not how one capability is composed from more than one component. Nothing in the file states that a capability delivered as an MCP server or a hook also needs a model-facing consumer — a skill or agent that tells the model when and how to invoke it. A plugin can therefore pass the skill's guidance while shipping tools that no skill or agent ever routes to.

### Target state

`component-patterns/SKILL.md` carries a completeness step after the selection tree: for the component type selected, name which companion component(s) must ship for the capability to be reachable by a model. The MCP-server case is stated explicitly — the server plus the skill or agent that documents when to call its tools — and the same check applies to hooks that inject context no runtime text explains.

### Measurable signal

- `grep -n "model-facing" plugins/plugin-creator/skills/component-patterns/SKILL.md` returns a match inside a completeness section (not only in a SOURCE line).
- The MCP leaf of the selection tree routes onward to the pairing requirement instead of terminating at "Use an MCP Server".
- A plugin review run through this skill reports an MCP server whose tools are referenced by no skill or agent in the same plugin as incomplete, rather than as correctly structured.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| DeepSeek Harness as a fifth entry in `harness_compatibility.json` (`harnesses` currently lists claude-code, codex, hermes, kimi) — the entry documents a `hooks/` package providing "Hook bridges + the shared Claude Code / Codex wire-protocol library" (line 62) | Medium | The entry establishes only that dsh speaks the Claude Code hook wire protocol. It does not state that dsh loads Claude Code plugin manifests, skills, or agents. Adding a harness column commits every plugin to a compatibility claim that no read source supports. Raise confidence by verifying against the dsh repository whether a `.claude-plugin/plugin.json` plugin is loadable, and whether a `SKILL.md` is discovered. The harness is also in developer preview with declared compatibility-breaking changes (lines 181-189), so the matrix entry would need re-verification on every dsh release. |
| Snapshot tests that "replay recorded sessions through the same profiles" (line 68) applied to `.claude/skills/session-historian/SKILL.md`, which indexes `~/.claude/projects/` JSONL transcripts for recall only | Medium | dsh owns its own execution loop and can therefore replay a session deterministically. This repo ships markdown skills consumed by harnesses it does not control, so a recorded Claude Code transcript is not re-executable through the same path. A compatible weaker form — using recorded transcripts as an activation-evaluation corpus — is plausible but is not the pattern the entry describes, and overlaps existing evaluation work (`research/insights/2026-05-09-agent-skills-eval-improvements.md`). Raise confidence by determining whether any harness this repo targets exposes a replay entry point. |
| "Model-visible ⟺ logged: anything that reaches a model request must be reconstructable from the session log; a new model-visible input requires a session event" (line 56) | Low | The rule presumes ownership of a session event store. This repo's nearest equivalents — the dh artifact manifest and SAM task records — already persist what stages hand to each other, and the remaining model-visible injections (hook-injected rule pointers, skill loads) are written by harnesses this repo does not own. Whether an unlogged model-visible input actually exists here was not established by reading any file; the gap is inferred. Raise confidence by auditing one dispatch path end to end for inputs that reach a subagent prompt and are recorded nowhere readable. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Provider swapping via configuration — "Extension plugins depend on Service Definitions, never concrete providers" (line 97), plugins loaded from a `cordis.yml` profile | Already covered. `plugins/development-harness/AGENTS.md` "Composition Model" maps abstract roles to concrete agents through a language manifest resolved at runtime, with `dh:task-worker` as the fallback when no manifest matches, and `docs/backend-providers.md` defines the `WorkItemBackend`/`ContentProvider`/`TaskBackend` protocol split with independently selectable `github`/`sqlite`/`memory`/`beads` families. This is the same definition-vs-provider separation, already implemented. (The narrower question of whether dh profiles support overlay/conditional composition is recorded above as unexamined.) |
| Plugin discovery by GitHub topic (`dsh-plugin`), with the loader resolving plugins from workspace, NPM registry, or GitHub (lines 109, 199) | Incompatible with the consuming harness. Claude Code discovers plugins through marketplace manifests — this repo's `.claude-plugin/marketplace.json`, per `AGENTS.md` Repository Overview — not through repository topics, and no entry in the research file claims otherwise. Tagging the repository would affect GitHub search results only, changing nothing an agent reads. |
