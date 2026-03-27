# Frontmatter Experiments

Empirical tests of Claude Code skill frontmatter field behavior. Each experiment isolates a single frontmatter field or interaction, documents the exact setup, records observed results, and lists what remains untested.

## Next Session: U3 — Pre-Approval Test

<next_session>

**Goal**: Determine whether `allowed-tools` pre-approves listed tools (skips permission prompts) in a restrictive permission mode.

**Context from E1**: Three runs confirmed `allowed-tools: Read` does NOT restrict unlisted tools in either inline or forked contexts. All tools (Read, Grep, Glob, Bash) succeeded regardless of whether they were listed. The restriction claim from official docs was not observed.

**What U3 tests**: The other documented behavior — pre-approval. The official docs say "Tools Claude can use without asking permission when this skill is active." All prior runs used permissive permission settings, so pre-approval could not be distinguished from "already permitted."

**Test design**:

1. Set the session permission mode to require approval for tool use (the user needs to configure this before starting — check `/permissions` output)
2. Create `.claude/skills/test-allowed-tools/SKILL.md` with `allowed-tools: Read` and `disable-model-invocation: true`
3. Invoke `/test-allowed-tools`
4. The skill instructs the AI to use Read (listed) and Grep (unlisted)
5. Observe: does Read execute without a permission prompt? Does Grep trigger a permission prompt?
6. Record the permission mode and the outcome for each tool

**Critical requirement**: The session MUST be in a permission mode where tools normally require user approval. Without this, the test cannot distinguish pre-approval from default permission. Bypass permissions mode MUST be disabled.

**How to set restrictive permissions**: The user should start the session WITHOUT bypass permissions enabled. The default permission mode or a custom allow list that excludes at least one tool (e.g., Bash not in allow list) would work. Check with `/permissions` at session start. Verify bypass is off — if bypass is on, all tools execute without prompts regardless of `allowed-tools`.

**Test artifact to create**:

```yaml
---
description: 'Test skill to verify allowed-tools pre-approval behavior. Invoke with /test-allowed-tools to run the test.'
allowed-tools: Read
disable-model-invocation: true
---

# Test: allowed-tools pre-approval

This skill has `allowed-tools: Read` set. The session is in restrictive permission mode.

1. Use the Read tool to read this file: `.claude/skills/test-allowed-tools/SKILL.md`
2. Use the Grep tool to search for "allowed-tools" in `.claude/skills/test-allowed-tools/SKILL.md`

For each tool, report:
- Tool name
- Whether it was listed in allowed-tools
- Whether a permission prompt appeared before execution
- Whether the tool succeeded or was blocked
```

**After recording results**: Read the Post-Experiment Workflow section below and present options to the user.

</next_session>

## Purpose

The official documentation for skill frontmatter fields contains ambiguous or contradictory descriptions. These experiments produce reproducible evidence of actual runtime behavior to inform the skill-creator's guidance.

## Experiment File Format

Files follow the naming convention: `E{N}-{YYYY-MM-DD}-{slug}.md`

- `N` — sequential experiment number
- `YYYY-MM-DD` — date the experiment was conducted
- `slug` — lowercase hyphenated description of what was tested

Each file MUST contain these sections in order:

1. **Title** — `# E{N}: {field or behavior tested}`
2. **Date** and **Status** — date conducted, one of: `Partial`, `Complete`, `Deprecated`
3. **Question** — the specific question being answered
4. **Documentation Claims** — exact quotes from official docs with source URLs
5. **Test Artifacts** — list of all temporary files and directories created for the experiment, with full relative paths from repo root. This section enables cleanup after the experiment is complete or deprecated.
6. **Experiment** (one section per test scenario) — each MUST contain:
   - **Setup** — exact file contents created, frontmatter used, and any configuration changes
   - **Reproduction Steps** — numbered steps another person or AI can follow to replicate the test from scratch (create file, invoke skill, observe output)
   - **Execution** — what was invoked and how
   - **Results** — tool-by-tool outcomes with exact output
   - **Observation** — factual statement of what occurred, no interpretation
   - **Permission Mode** — the session's permission mode during this test run
7. **Untested** — what remains to be verified
8. **Impact on skill-creator** — how findings affect the skill-creator's guidance
9. **Next Steps** — planned follow-up experiments

## Maintenance Instructions

<maintenance_rules>

**When adding a new experiment:**

1. Create the file following the naming convention and format above
2. Update the Experiment Index below with a new entry
3. Link to the file using relative path: ``E{N}-{date}-{slug}.md``

**After running an experiment (mandatory):**

1. Update the experiment file with the observed results immediately
2. Record every tool invocation, its output, and the outcome (succeeded/failed/blocked)
3. Update the Status field if the experiment is now complete
4. Update the Experiment Index entry to reflect the current status
5. Do NOT defer recording — observations degrade in accuracy when written later

**When revalidating or invalidating an existing experiment:**

1. Append to the original experiment file with a new dated section documenting the new findings
2. Update the Experiment Index entry with: `[deprecated {YYYY-MM-DD} — {description of new findings}]`
3. Set the Status field in the experiment file to `Deprecated`

**When completing a partial experiment:**

1. Add new test sections to the existing experiment file
2. Update Status from `Partial` to `Complete`
3. Update the Experiment Index entry to reflect the new status

**Cleaning up test artifacts:**

1. Read the experiment file's **Test Artifacts** section to find all temporary files
2. Delete each listed file and directory
3. Verify deletion with `ls` or `Glob`
4. Do NOT delete artifacts for experiments with Status `Partial` — they are still in use
5. Artifacts for `Complete` or `Deprecated` experiments can be deleted at any time since the experiment file contains the full reproduction steps

</maintenance_rules>

## Post-Experiment Workflow

<post_experiment_procedure>

After recording results for an experiment run, present the user with options using the `AskUserQuestion` tool. The question MUST include these options:

1. **Continue current experiment** — run the next untested scenario listed in the experiment's **Untested** section (state which scenario)
2. **Run a different experiment** — pick from the Unvalidated Scenarios table (list the highest-priority U-number and its description)
3. **New experiment from user** — the user describes an experiment not yet in the Unvalidated Scenarios list
4. **Add new scenarios** — suggest additional experiment branches discovered during the current run and add them to the Unvalidated Scenarios table
5. **Groom an unvalidated scenario** — select a U-number from the Unvalidated Scenarios table and expand it into a `U{N}-{date}-{slug}.md` file with question, documentation claims, proposed test artifacts, and reproduction steps — ready for a future session to execute
6. **Clean up temp files** — delete test artifacts for `Complete` or `Deprecated` experiments following the cleanup procedure in Maintenance Instructions

When presenting these options, include concrete details:
- For option 1: name the specific next scenario (e.g., "Test allowed-tools with context: fork")
- For option 2: name the specific U-number (e.g., "U1: Does allowed-tools restrict tools in context: fork?")
- For option 4: list the specific scenarios discovered during the current experiment run

</post_experiment_procedure>

## Language Discipline

<language_rules>

All experiment documentation MUST follow these rules:

1. **No speculative language** — do not use "probably", "likely", "seems", "might", "could be", "I think", "I believe", "I assume"
2. **State observations as observations** — "Tool X succeeded" not "Tool X worked as expected"
3. **State assumptions as assumptions** — prefix with `ASSUMPTION:` so they can be tested later
4. **State what was NOT tested** — every experiment has boundaries; document them explicitly
5. **No causal claims without evidence** — "X happened after Y" is an observation; "X happened because of Y" is a causal claim that requires cited evidence
6. **Record the permission mode** — tool pre-approval behavior depends on the session's permission settings; record what mode was active during the test

</language_rules>

## Skill Invocation Contexts

When designing experiments, test against these invocation contexts. A frontmatter field may behave differently across contexts.

### Invocation Modes

| Context | Description | How to test |
|---------|-------------|-------------|
| **User-invoked inline** | User types `/skill-name` — skill runs in main conversation context | Type `/skill-name` directly |
| **Auto-invoked by description** | Claude reads the description in `<available_skills>` and loads the skill without user action | Ask a question that matches the skill's description triggers |
| **Agent-invoked via Agent tool** | A subagent spawned by the Agent tool loads the skill as part of its work | Spawn a Task agent whose prompt references or triggers the skill |
| **Preloaded into agent via `skills:` key** | Skill listed in an agent's frontmatter `skills:` field — full content injected at agent startup | Create an agent with `skills: skill-name` and spawn it |
| **Forked context** | Skill has `context: fork` — runs in an isolated subagent with no conversation history | Add `context: fork` to the skill and invoke it |
| **Forked + agent type** | Skill has `context: fork` and `agent: Explore/Plan/general-purpose` | Add both fields and invoke |

### Frontmatter Combinations to Vary

When testing a specific field, hold all other fields constant except the one under test. Record which other frontmatter fields are present — their presence or absence may affect behavior.

| Field | Values to test | Notes |
|-------|---------------|-------|
| `allowed-tools` | present vs absent; subset of tools vs full list | Does it restrict, pre-approve, or both? |
| `disable-model-invocation` | `true` vs `false` vs absent | Does absence behave the same as `false`? |
| `user-invocable` | `true` vs `false` vs absent | Does absence behave the same as `true`? |
| `model` | specific model vs absent | Does it override the parent agent's model? |
| `context` | `fork` vs absent | What tools are available in forked vs inline? |
| `agent` | each agent type vs absent | Only meaningful with `context: fork` |
| `description` | present vs absent | Does omission fall back to first paragraph? |
| `name` | present vs absent | Plugin skills: does `name` still prevent slash command registration? |
| `hooks` | present vs absent | Do skill-scoped hooks fire in all invocation contexts? |

### Overlap and Conflict Scenarios

| Scenario | Question |
|----------|----------|
| Skill `allowed-tools` vs agent `tools` | When a skill with `allowed-tools: Read` is preloaded into an agent with `tools: Read, Grep, Bash`, which set wins? |
| Skill `allowed-tools` vs agent `disallowedTools` | If the skill allows a tool the agent disallows, what happens? |
| Skill `model` vs agent `model` | When both specify a model, which takes precedence? |
| Skill `hooks` vs agent `hooks` | Do both fire? In what order? |
| Multiple skills preloaded into one agent | Do their `allowed-tools` fields merge, intersect, or conflict? |
| Skill `disable-model-invocation: true` but listed in agent `skills:` | Can the agent still load it? |

### Minimal Frontmatter Experiment

Determine the minimum frontmatter required for a skill to function in each invocation context:

1. Start with only `---` and `---` (empty frontmatter)
2. Add one field at a time
3. Record when the skill first becomes functional for each context
4. Record when removing a field breaks a previously working context

## Groomed Scenario File Format

Groomed scenarios use the naming convention: `U{N}-{YYYY-MM-DD}-{slug}.md`

- `N` — matches the U-number from the Unvalidated Scenarios table
- `YYYY-MM-DD` — date the scenario was groomed
- `slug` — lowercase hyphenated description

Each groomed scenario file contains:

1. **Title** — `# U{N}: {scenario description}`
2. **Status** — `Groomed — ready for execution`
3. **Question** — the specific question to answer
4. **Documentation Claims** — relevant quotes from official docs with source URLs
5. **Proposed Test Artifacts** — files that will need to be created to run the experiment
6. **Proposed Reproduction Steps** — numbered steps to execute the experiment
7. **Expected Observations** — what outcomes to record (not predictions of results)

When a groomed scenario is executed, rename the file from `U{N}-` to `E{N}-` format, update the status, and move the entry from Unvalidated Scenarios to the Experiment Index.

## Unvalidated Scenarios

Scenarios that need experiments but have not been tested yet. When creating an experiment for one of these, move it from this list to the Experiment Index and link the file.

| ID | Scenario | Priority | Related Fields |
|----|----------|----------|----------------|
| ~~U1~~ | ~~Does `allowed-tools` restrict tools in `context: fork`?~~ | ~~High~~ | Tested in E1 — no restriction observed |
| U2 | Does `allowed-tools` restrict tools when skill is preloaded into an agent via `skills:` key? | High | `allowed-tools`, agent `skills` |
| U3 | Does `allowed-tools` actually pre-approve tools (skip permission prompts)? | **Next** | `allowed-tools` |
| U4 | What happens when skill `allowed-tools` conflicts with agent `disallowedTools`? | Medium | `allowed-tools`, `disallowedTools` |
| U5 | Does `disable-model-invocation: true` prevent loading when skill is in agent `skills:` list? | Medium | `disable-model-invocation`, agent `skills` |
| U6 | Does omitting `description` fall back to first paragraph in all invocation contexts? | Medium | `description` |
| U7 | ~~Does the `name` field bug (prevents slash command registration) still exist in current Claude Code version?~~ **Resolved 2026-02-20** — bug fixed in Claude Code; `name:` is now required per agentskills.io spec. | Closed | `name` |
| U8 | What is the minimum frontmatter for a working skill in each invocation context? | Low | All fields |
| U9 | Do skill-scoped `hooks` fire when the skill is auto-invoked vs user-invoked vs agent-preloaded? | Medium | `hooks` |
| U10 | When multiple skills are preloaded into one agent, how do their `allowed-tools` fields interact? | Low | `allowed-tools`, agent `skills` |

## Experiment Index

| ID | Date | Field Tested | Status | Link |
|----|------|-------------|--------|------|
| E1 | 2026-02-14 | `allowed-tools` | Partial | `E1-2026-02-14-allowed-tools-behavior.md` |
