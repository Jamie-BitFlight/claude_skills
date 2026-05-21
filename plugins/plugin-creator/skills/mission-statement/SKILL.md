---
name: mission-statement
description: Define and develop plugin mission statements — purpose, values, anti-patterns, and trade-offs. Use when creating a new plugin, auditing an existing plugin's alignment, or providing a reference for the alignment check loop to evaluate decisions against. Produces mission.json with [draft] status and creates a backlog interview task for the human to refine it.
argument-hint: <plugin-path>
model: sonnet
user-invocable: true
---
If the user's intent does not match the purpose of this skill, load `plugin-lifecycle` to route to the right skill and process: `Skill(skill="plugin-creator:plugin-lifecycle")`.


<invocation_args>$ARGUMENTS</invocation_args>

# Mission Statement

## What It Is (and Isn't)

A plugin mission statement is a **decision-making anchor**, not a feature description. It states what the plugin values, what it refuses to do, and how it resolves trade-offs — enabling AI agents to evaluate alignment without asking the human each time.

| Mission Statement Is | Mission Statement Is Not |
|---------------------|--------------------------|
| A decision-making anchor | A feature list or capability overview |
| An explicit anti-pattern registry | A marketing or sales description |
| A trade-off resolution guide | A roadmap or version history |
| A verifiable alignment reference | A technical specification |

## The `mission.json` Format

The file lives at the **plugin root** (not in `.claude/plan/`).

```json
{
  "status": "draft",
  "mission": "One sentence. What this plugin is trying to be — not what it does.",
  "values": [
    "Value statement 1 — concrete, verifiable",
    "Value statement 2"
  ],
  "anti_patterns": [
    "Specific behavior this plugin refuses to do",
    "Another explicit refusal"
  ],
  "escalation_triggers": [
    "keyword", "another keyword phrase"
  ],
  "trade_offs": {
    "correctness_vs_speed": "correctness",
    "breadth_vs_depth": "depth",
    "explicit_vs_implicit": "explicit"
  },
  "out_of_scope": [
    "Thing that looks related but belongs elsewhere"
  ],
  "interview_backlog_item": "#NNN",
  "validated_scenarios": []
}
```

Field definitions:

- `status` — `"draft"` until interview completes and human approves; then `"active"`
- `mission` — single sentence; must pass the "bad twin" test (a bad version of this plugin could not claim the same statement)
- `values` — observable principles that guide decisions; must be verifiable against behavior
- `anti_patterns` — explicit refusals; what this plugin will not do even when asked
- `escalation_triggers` — keyword list for fast string-match in alignment checks; no LLM needed
- `trade_offs` — when forced to choose, which side does this plugin take
- `out_of_scope` — things that look adjacent but belong in other plugins
- `interview_backlog_item` — GitHub issue number of the interview task (added after backlog creation)
- `validated_scenarios` — list of known past decisions that this statement correctly predicts

## Development Process

Three phases:

1. **AI Draft** (immediate, this session) — source: discussion context + plugin files. Output: `mission.json` with `status: "draft"`. The `[draft]` tag signals this is a hypothesis, not a decision.
2. **Interview** (async, via backlog task) — five structured questions asked to the human. Raw answers captured in backlog item. Output: updated `mission.json` with human-verified values.
3. **Validation** (after interview) — run 3 known past decisions through the statement. Does it predict the right choice? Output: `validated_scenarios` populated; `status: "active"`.

## The Five Interview Questions

These questions surface actual values, not stated ones. Ask them in order.

**Q1 — The Non-Negotiable**

> "What is the one thing this plugin must never sacrifice, even to ship faster?"

Anchors `values[0]` — the primary principle.

**Q2 — The Bad Twin**

> "What would a superficially similar but wrong version of this plugin do? What makes it wrong?"

Populates `anti_patterns`. A good mission statement the bad twin cannot also claim.

**Q3 — The Trade-off**

> "When forced to choose between [breadth vs depth / correctness vs speed / explicit vs implicit], which does this plugin choose, and why?"

Ask all three. If the human says "both" — ask "if you could only have one." Answers populate `trade_offs`.

**Q4 — The Removal Trigger**

> "What would make you remove this plugin from the marketplace entirely?"

Populates the most severe `anti_patterns` and `escalation_triggers`.

**Q5 — The Anti-Pattern Example**

> "Give me a specific example of a 'fix' or 'improvement' this plugin should refuse to make, even if asked."

Most useful for alignment checks. Concrete refusals become `escalation_triggers` keywords.

## AI Draft Procedure

When invoked (during Phase 0.6 of plugin lifecycle, or standalone):

1. Read the plugin's existing files: `plugin.json` or `.claude-plugin/plugin.json`, `CLAUDE.md` if present, `SKILL.md` files
2. Read `discuss-CONTEXT.md` if this is a new plugin creation
3. Draft `mission.json` with `status: "draft"`. Populate all fields from observed design choices and stated preferences.
4. Write `mission.json` to the plugin root directory
5. Create a backlog interview task via `mcp__plugin_dh_backlog__backlog_add` with title `"Mission interview: {plugin-name}"` and body containing the 5 questions and the current draft mission field
6. Update `mission.json` with `"interview_backlog_item": "#NNN"` using the created issue number
7. Report: path of draft written, backlog item number, 2-3 sentence summary of draft mission

## Validation Scenario Format

After interview, validate by running known decisions through the statement. Add each to `validated_scenarios`:

```json
{
  "validated_scenarios": [
    {
      "decision": "Refused to add blanket noqa suppression to a linting plugin",
      "predicted_by": "anti_patterns[0] + escalation_triggers",
      "outcome": "correct"
    }
  ]
}
```

Status becomes `"active"` when it correctly predicts at least 3 known decisions.

## Standalone Invocation

Arguments: `<invocation_args/>`

- `<plugin-path>` — Draft mission for an existing plugin. Read plugin files, draft `mission.json`, create backlog interview item.
- `<plugin-path> --interview` — Conduct the interview synchronously in this session. Ask Q1-Q5, update `mission.json` from answers, move to validation.
- `<plugin-path> --validate` — Run validation scenarios. Ask human to confirm 3 past decisions, check predictions.

## Relationship to Alignment Check

The `escalation_triggers` list is the fast path for alignment checking — pure string matching, no LLM:

1. Check proposed action text against `escalation_triggers` — if any keyword matches, escalate immediately
2. If no keyword match, check `anti_patterns` with LLM reasoning against mission and values
3. If action contradicts `anti_patterns` or moves away from `values`, return `alignment: LOW` with the specific violated principle

The mission statement answers "what would the human say if they were watching?" — codified in advance.
