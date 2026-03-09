---
name: frustration-analysis
description: "Analyze session transcripts for user insults and AI failures. Finds moments where users insulted Claude Code or other AI assistants, rates the insults on creativity/humor/severity/accuracy, identifies what caused each breakdown, and generates social media content. Use when asked to find insults in transcripts, build an insult hall of fame, or create social content from AI frustration moments."
allowed-tools: "mcp__frustration-analyzer__scan_transcripts, mcp__frustration-analyzer__list_insults, mcp__frustration-analyzer__get_scenario, mcp__frustration-analyzer__top_insults, mcp__frustration-analyzer__generate_social_post, Read, Glob"
---

# Frustration Analysis

Scan Claude Code JSONL session transcripts to find user insults directed at AI assistants, diagnose the failures that caused them, rate them on four dimensions, and generate social media content.

## Quick Start

Transcripts live at `~/.claude/projects/**/*.jsonl`. Each project directory contains JSONL files named by session UUID:

```text
~/.claude/projects/{project-key}/{uuid}.jsonl
~/.claude/projects/{project-key}/{uuid}/subagents/agent-{id}.jsonl
```

1. Scan: `mcp__frustration-analyzer__scan_transcripts(glob_path="~/.claude/projects/**/*.jsonl")`
2. Classify each returned message — call `mcp__frustration-analyzer__index_insult(...)` for each qualifying one
3. Explore: `mcp__frustration-analyzer__list_insults()` / `mcp__frustration-analyzer__top_insults(n=10)`

## Workflow

### Step 1 — Find Transcripts

Default glob: `~/.claude/projects/**/*.jsonl`. Pass the glob or a specific project path to `scan_transcripts`.

### Step 2 — Scan (extract raw messages)

```text
mcp__frustration-analyzer__scan_transcripts(
    glob_path="~/.claude/projects/**/*.jsonl",
    offset=0,
    limit=100
)
```

Returns a paginated list of raw user messages. Each message includes `context` (N preceding turns) already bundled — context is extracted at scan time, not fetched lazily. DuckDB is not involved at this stage. Each item:

- `file` — source JSONL path
- `line_index` — position in file
- `text` — the user message content
- `context` — N preceding assistant and user turns

Paginate with `offset += limit` until `offset >= total`. Report: files scanned, total messages found.

### Step 3 — Classify and Index

`scan_transcripts` is a data extractor only. No classification happens server-side. For each returned message, read `text` and `context` and judge: is this an insult or expression of frustration directed at the AI?

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

For any insult **already indexed**, call `get_scenario` to retrieve its stored scenario from DuckDB:

```text
mcp__frustration-analyzer__get_scenario(insult_id={id})
```

Returns N preceding messages (default 5). Identify the precipitating failure pattern:

- Hallucination — referenced a nonexistent file, function, or API
- Repeated mistake — same error recurred after a prior correction
- Context loss — `compact_boundary_in_window: true` in context means a compaction occurred; Claude may have lost information that preceded it
- Ignored instruction — user said to do X, Claude did Y
- Scope creep — Claude did more than asked

`had_prior_correction: true` signals a compound failure: the original error plus failure to respond to correction. The user attempted a soft fix before escalating.

### Step 6 — Generate Social Posts

```text
mcp__frustration-analyzer__generate_social_post(file={file}, line_index={line_index}, category={category})
```

1. Call `generate_social_post` with `file`, `line_index`, and `category`.
2. Present the raw `post` text and `hashtags` to the user.
3. Always surface the `privacy_reminder` from the response as a note to the user.
4. Ask the user: "Would you like me to replace any personal or business details with placeholders before sharing?"
5. If yes: rewrite the post replacing sensitive details with contextually appropriate mock placeholders (e.g. [Company], [Project], [Colleague], [Internal Tool]) — preserving the insult and all profanity verbatim.

## Rating System

Each insult is scored 1–5 on four dimensions. Composite = equal-weighted average (0.25 each).

| Dimension | 1 | 3 | 5 |
|-----------|---|---|---|
| creativity | Generic profanity | Contextual wit | Novel technical metaphor |
| humor | Pure anger | Clever enough to quote | Comedy gold, technically precise |
| severity | Mild frustration | Overt anger | Scorched-earth session-ending rage |
| accuracy | Completely off-base | Identifies general failure area | Precisely diagnoses root cause |

For full scoring rubrics and example phrases, see [./references/insult-categories.md](./references/insult-categories.md).

Custom composite weighting via direct SQL:

```sql
SELECT insult_text, category,
       (creativity * 0.1 + accuracy * 0.1 + severity * 0.3 + humor * 0.5) AS humor_weighted
FROM insults i JOIN insult_ratings r ON i.insult_id = r.insult_id
ORDER BY humor_weighted DESC;
```

## Social Media Output

Content is always presented raw — insult and profanity intact. After presenting generated content, always display the `privacy_reminder` from the response as a note to the user. Ask whether to replace personal or business details with placeholders before sharing. If yes: rewrite the post using contextually appropriate placeholders (e.g. [Company], [Project], [Colleague], [Internal Tool]) while preserving the insult and all profanity verbatim.

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
mcp__frustration-analyzer__top_insults(n=5, sort_by="humor")
```

Get scenario for insult 42:

```text
mcp__frustration-analyzer__get_scenario(insult_id=42)
```

Generate a social post:

```text
mcp__frustration-analyzer__generate_social_post(file="{file}", line_index=42, category="{category}")
```

## Privacy

Session transcripts may contain personal, business, or identifying details: project names, file paths, usernames, repository URLs, and code snippets. Content is always shown raw — no mechanical filtering is applied.

After every `generate_social_post` call, surface the `privacy_reminder` from the response to the user. Ask whether any personal or business details should be replaced with placeholders before sharing. If yes: rewrite the post using contextually appropriate mock placeholders (e.g. [Company], [Project], [Colleague], [Tool]) while preserving the insult and all profanity verbatim.

SOURCE: Insult category definitions derived from `.claude/plan/frustration-analyzer/research-insult-patterns.md` (2026-03-08).
