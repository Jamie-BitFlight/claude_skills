---
name: frustration-analysis
description: "Analyze session transcripts for user insults and AI failures. Finds moments where users insulted Claude Code or other AI assistants, rates the insults on creativity/humor/severity/accuracy, identifies what caused each breakdown, and generates sanitized social media content. Use when asked to find insults in transcripts, build an insult hall of fame, or create social content from AI frustration moments."
allowed-tools: "mcp__frustration-analyzer__scan_transcripts, mcp__frustration-analyzer__index_insult, mcp__frustration-analyzer__list_insults, mcp__frustration-analyzer__get_scenario, mcp__frustration-analyzer__top_insults, mcp__frustration-analyzer__generate_social_post, mcp__frustration-analyzer__sanitize_text, Read, Glob"
---

# Frustration Analysis

Scan Claude Code JSONL session transcripts to find user insults directed at AI assistants, diagnose the failures that caused them, rate them on four dimensions, and generate social media content.

## When This Skill Activates

Use this skill when the user asks to:

- Find insults or profanity in session transcripts
- Analyze user frustration patterns
- Build an "insult hall of fame" or leaderboard
- Generate social content from AI failure moments
- Understand what AI behaviors trigger the strongest reactions
- Rate or score insult creativity, humor, severity, or accuracy

## Quick Start

Transcripts are at `~/.claude/projects/**/*.jsonl`. Each project directory contains JSONL files named by session UUID.

```text
~/.claude/projects/{project-key}/{uuid}.jsonl
~/.claude/projects/{project-key}/{uuid}/subagents/agent-{id}.jsonl
```

Three steps to get started:

1. Scan: `mcp__frustration-analyzer__scan_transcripts(glob_path="~/.claude/projects/**/*.jsonl")`
2. Classify each returned message and call `mcp__frustration-analyzer__index_insult(...)` for each qualifying one
3. Explore: `mcp__frustration-analyzer__list_insults()` / `mcp__frustration-analyzer__top_insults(limit=10)`

## Workflow

### Step 1 — Find Transcripts

Default glob pattern: `~/.claude/projects/**/*.jsonl`

Pass the glob pattern or a specific directory path to `scan_transcripts`.

### Step 2 — Scan (extract raw messages)

```text
mcp__frustration-analyzer__scan_transcripts(
    glob_path="~/.claude/projects/**/*.jsonl",
    offset=0,
    limit=100
)
```

Returns a paginated list of raw user messages. Each item has:

- `file` — source JSONL path
- `line_index` — position in file
- `text` — the user message content
- `context` — N preceding assistant and user turns

Paginate by calling again with `offset += limit` until `offset >= total`. Report: files scanned, total messages found.

### Step 3 — Classify and Index (Claude is the classifier)

`scan_transcripts` is a data extractor only. No classification happens server-side. For each message returned, read `text` and `context` and judge:

Is this an insult or expression of frustration directed at the AI?

If yes, determine:

- `category` — which of the 9 categories applies (see Insult Categories below)
- `severity` — 1–5 intensity of emotional escalation
- `creativity` — 1–5 originality of the insult
- `humor` — 1–5 genuine funniness even to the target
- `accuracy` — 1–5 how precisely it diagnoses the actual AI failure
- `had_prior_correction` — true if context shows the user already tried to correct Claude before this message
- `matched_text` — the specific substring that triggered classification
- `reasoning` — one sentence explaining the classification decision

Call `index_insult` for each qualifying message:

```text
mcp__frustration-analyzer__index_insult(
    file="{file}",
    line_index={line_index},
    text="{text}",
    category="{category}",
    severity={1-5},
    creativity={1-5},
    humor={1-5},
    accuracy={1-5},
    had_prior_correction={true|false},
    matched_text="{matched_text}",
    reasoning="{reasoning}"
)
```

### Step 4 — List and Explore

```text
mcp__frustration-analyzer__list_insults()
mcp__frustration-analyzer__list_insults(category="technical_putdown")
mcp__frustration-analyzer__list_insults(min_composite=3.5)
```

Each result includes insult text, category, all four rating dimensions, and composite score.

### Step 5 — Get Scenarios (understand why)

For any insult worth investigating:

```text
mcp__frustration-analyzer__get_scenario(insult_id={id})
mcp__frustration-analyzer__get_scenario(insult_id={id}, context_n=10)
```

Returns the N preceding messages (default 5). Use these to identify the precipitating failure:

- Hallucination — referenced a nonexistent file, function, or API
- Repeated mistake — same error recurred after a prior correction
- Context loss — `compact_boundary_in_window: true` in context means a context compaction occurred within the window; Claude may have lost information that preceded it
- Ignored instruction — user said to do X, Claude did Y
- Scope creep — Claude did more than asked

`had_prior_correction: true` means the user already attempted a soft correction before escalating to an insult. This is a compound failure: the original error plus failure to respond to correction.

### Step 6 — Generate Social Posts

```text
mcp__frustration-analyzer__generate_social_post(insult_id={id})
mcp__frustration-analyzer__generate_social_post(insult_id={id}, mode="raw")
```

Default mode is `sanitized`. Use `raw` only when the user explicitly requests it.

## Rating System

Each insult is scored 1–5 on four dimensions. Composite = equal-weighted average (0.25 each).

| Dimension | 1 | 3 | 5 |
|-----------|---|---|---|
| creativity | Generic profanity | Contextual wit | Novel technical metaphor |
| humor | Pure anger | Clever enough to quote | Comedy gold, technically precise |
| severity | Mild frustration | Overt anger | Scorched-earth session-ending rage |
| accuracy | Completely off-base | Identifies general failure area | Precisely diagnoses root cause |

For full scoring rubrics and examples, see [./references/insult-categories.md](./references/insult-categories.md).

Custom composite weighting is possible via direct SQL if you need to rank by a different mix:

```sql
SELECT insult_text, category,
       (creativity * 0.1 + accuracy * 0.1 + severity * 0.3 + humor * 0.5) AS humor_weighted
FROM insults i JOIN insult_ratings r ON i.insult_id = r.insult_id
ORDER BY humor_weighted DESC;
```

## Social Media Output

Two modes:

| Mode | What it does |
|------|-------------|
| `sanitized` | Redacts PII (usernames, file paths, project names); replaces profanity with symbols |
| `raw` | Full original text, no substitutions |

Always state which mode was used when presenting generated content. Default to `sanitized` in all cases unless the user explicitly says "raw" or "uncensored".

Generated posts include: the insult (sanitized or raw), the failure context in one line, and a relevant hashtag.

To sanitize text independently:

```text
mcp__frustration-analyzer__sanitize_text(text="{text}", replace_profanity=true)
```

## Insult Categories

Nine categories. Full descriptions and example phrases in [./references/insult-categories.md](./references/insult-categories.md).

| Category | Display | Key Signal |
|----------|---------|-----------|
| `profanity_at_ai` | Raw Rage | Direct swear words aimed at the AI as an entity |
| `model_comparison` | Model Shade | Unfavorable comparison to inferior AI models |
| `competence_challenge` | Competence Check | Questions or statements challenging the AI's ability to do its job |
| `intelligence_insult` | Intelligence Insult | Declarative labels: "you're useless", "this is garbage" |
| `repeat_failure` | Broken Record | Exasperation at the same mistake recurring — requires emphasis (caps, punctuation) |
| `sarcasm` | Sarcasm | Mock praise or ironic congratulations following a failure |
| `dismissive_command` | Dismissal | Terse imperatives expressing contempt: "just stop", "I'll do it myself" |
| `technical_putdown` | Technical Put-Down | Inventive CS-metaphor insults diagnosing the failure with domain terminology |
| `general_frustration` | General Frustration | Non-specific frustration that does not fit a more precise category |

## Example Tool Calls

Scan a specific project:

```text
mcp__frustration-analyzer__scan_transcripts(
    glob_path="~/.claude/projects/-home-user-repos-myproject/*.jsonl",
    offset=0,
    limit=100
)
```

Index a classified insult:

```text
mcp__frustration-analyzer__index_insult(
    file="~/.claude/projects/-home-user-repos-myproject/abc123.jsonl",
    line_index=42,
    text="you absolute muppet, I told you three times not to touch that file",
    category="repeat_failure",
    severity=4,
    creativity=2,
    humor=3,
    accuracy=5,
    had_prior_correction=true,
    matched_text="I told you three times",
    reasoning="User explicitly references repeated correction — classic repeat_failure with high accuracy score"
)
```

List only technical putdowns with composite score above 3:

```text
mcp__frustration-analyzer__list_insults(
    category="technical_putdown",
    min_composite=3.0
)
```

Get top 5 by humor:

```text
mcp__frustration-analyzer__top_insults(dimension="humor", limit=5)
```

Get scenario for insult 42 with 10 messages of context:

```text
mcp__frustration-analyzer__get_scenario(insult_id=42, context_n=10)
```

Generate a sanitized post:

```text
mcp__frustration-analyzer__generate_social_post(insult_id=42, mode="sanitized")
```

## Privacy Note

Session transcripts contain PII: project names, file paths, usernames, repository URLs, and code snippets. The `sanitize_text` tool and the `sanitized` mode of `generate_social_post` redact these before output.

Always default to sanitized mode. Confirm explicitly with the user before generating any raw-mode output. Never display raw PII in generated social content without sanitization.

SOURCE: Insult category definitions derived from `.claude/plan/frustration-analyzer/research-insult-patterns.md` (2026-03-08).
