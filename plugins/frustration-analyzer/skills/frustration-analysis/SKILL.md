---
name: frustration-analysis
description: "Analyze session transcripts for user insults and AI failures. Finds moments where users insulted Claude Code or other AI assistants, rates the insults on creativity/humor/severity/accuracy, identifies what caused each breakdown, and generates sanitized social media content. Use when asked to find insults in transcripts, build an insult hall of fame, or create social content from AI frustration moments."
allowed-tools: "mcp__frustration-analyzer__scan_transcripts, mcp__frustration-analyzer__list_insults, mcp__frustration-analyzer__get_scenario, mcp__frustration-analyzer__top_insults, mcp__frustration-analyzer__generate_social_post, mcp__frustration-analyzer__sanitize_text, Read, Glob"
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

1. Scan transcripts: `mcp__frustration-analyzer__scan_transcripts(path="~/.claude/projects/**/*.jsonl")`
2. List insults: `mcp__frustration-analyzer__list_insults()`
3. Get top insults: `mcp__frustration-analyzer__top_insults(limit=10)`

## Workflow

### Step 1 — Find Transcripts

If the user has not provided a path, use Glob to locate transcript files:

```text
Pattern: ~/.claude/projects/**/*.jsonl
```

Pass the glob pattern or a specific directory to `scan_transcripts`.

### Step 2 — Scan

```text
mcp__frustration-analyzer__scan_transcripts(path="{transcript_path}")
```

The scanner reads each `type: "user"` record (excluding `toolUseResult` records), applies the eight insult category patterns, and stores matches in DuckDB with category, timestamp, session ID, and matched pattern.

Report: sessions scanned, insults found, breakdown by category.

### Step 3 — List and Explore

```text
mcp__frustration-analyzer__list_insults()
mcp__frustration-analyzer__list_insults(category="technical_putdown")
mcp__frustration-analyzer__list_insults(min_composite=3.5)
```

Each result includes insult text, category, all four rating dimensions, and composite score.

### Step 4 — Get Scenarios

For any insult you want to understand:

```text
mcp__frustration-analyzer__get_scenario(insult_id={id})
mcp__frustration-analyzer__get_scenario(insult_id={id}, context_n=10)
```

Returns the N preceding messages (default 5). Look for:

- The precipitating failure type (hallucination, ignored instruction, repeated mistake, context loss, etc.)
- Whether a soft correction preceded the insult (`had_prior_correction`)
- Whether a `compact_boundary` fell within the window (possible context loss as root cause)

### Step 5 — Generate Social Posts

```text
mcp__frustration-analyzer__generate_social_post(insult_id={id})
mcp__frustration-analyzer__generate_social_post(insult_id={id}, mode="raw")
```

Default mode is `sanitized`. Only use `raw` when the user explicitly requests it.

## Rating System

Each insult is scored 1–5 on four dimensions. Composite = equal-weighted average (0.25 each).

| Dimension | 1 | 3 | 5 |
|-----------|---|---|---|
| **Creativity** | Generic profanity | Contextual wit | Novel technical metaphor |
| **Humor** | Pure anger | Clever enough to quote | Comedy gold, technically precise |
| **Severity** | Mild frustration | Overt anger | Scorched-earth session-ending rage |
| **Accuracy** | Completely off-base | Identifies general failure area | Precisely diagnoses root cause |

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

Eight categories, ordered from least to most technically inventive. Full descriptions and example phrases in [./references/insult-categories.md](./references/insult-categories.md).

| Category | Key Signal |
|----------|-----------|
| `profanity_at_ai` | Direct swear words aimed at the AI as an entity |
| `model_comparison` | Unfavorable comparison to inferior AI models |
| `competence_challenge` | Questions or statements challenging the AI's ability to do its job |
| `intelligence_insult` | Declarative labels: "you're useless", "this is garbage" |
| `repeat_failure` | Exasperation at the same mistake recurring — requires emphasis (caps, punctuation) |
| `sarcasm` | Mock praise or ironic congratulations following a failure |
| `dismissive_command` | Terse imperatives expressing contempt: "just stop", "I'll do it myself" |
| `technical_putdown` | Inventive CS-metaphor insults diagnosing the failure with domain terminology |

## Example Tool Calls

Scan a specific project:

```text
mcp__frustration-analyzer__scan_transcripts(
    path="~/.claude/projects/-home-user-repos-myproject/*.jsonl"
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

Generate a sanitized tweet:

```text
mcp__frustration-analyzer__generate_social_post(insult_id=42, mode="sanitized")
```

## Privacy Note

Session transcripts contain PII: project names, file paths, usernames, repository URLs, and code snippets. The `sanitize_text` tool and the `sanitized` mode of `generate_social_post` redact these before output.

Always default to sanitized mode. Confirm explicitly with the user before generating any raw-mode output. Never display raw PII in generated social content without sanitization.

SOURCE: Insult category definitions and regex patterns derived from `.claude/plan/frustration-analyzer/research-insult-patterns.md` (2026-03-08). Rating dimension rubrics ibid.
