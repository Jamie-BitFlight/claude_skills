# frustration-analyzer

Analyzes Claude Code session transcripts to detect user insults directed at AI assistants, identify the failure scenarios that caused them, rate each insult on creativity, humor, severity, and accuracy, and generate social media content from the findings. It builds on the existing frustration signal detection in `agentskill-kaizen` (which covers soft signals like corrections and interrupts) and targets the harder signal class: explicit insults.

## Installation

```bash
claude plugin install frustration-analyzer@jamie-bitflight-skills
```

Or for local testing:

```bash
claude --plugin-dir ./plugins/frustration-analyzer
```

## Quick Start

1. Open a Claude Code session with the plugin loaded.
2. Find your transcripts:

   ```text
   Scan my transcripts for insults
   ```

3. Explore and generate:

   ```text
   Show me the top 10 most creative insults
   Generate a tweet for the funniest one
   ```

The plugin scans `~/.claude/projects/**/*.jsonl` by default.

## The 8 Insult Categories

| Category | Description |
|----------|-------------|
| `profanity_at_ai` | Direct swear words aimed at the AI as an entity |
| `model_comparison` | Unfavorable comparison to inferior AI models (Haiku, GPT-3, Copilot) |
| `competence_challenge` | Questions challenging the AI's ability to do its job ("can't you read?") |
| `intelligence_insult` | Declarative labels: "you're useless", "this is garbage" |
| `repeat_failure` | Exasperation at the same mistake recurring — requires emphasis (caps, `?!`) |
| `sarcasm` | Mock praise or ironic congratulations following a failure |
| `dismissive_command` | Terse imperatives: "just stop", "I'll do it myself", "I'm switching to Cursor" |
| `technical_putdown` | Inventive CS-metaphor insults diagnosing the failure mode ("off-by-one brain") |

## Rating Dimensions

Each insult is scored 1–5 on four dimensions. Composite = equal-weighted average.

| Dimension | What it measures | 5/5 example |
|-----------|-----------------|-------------|
| Creativity | How original and inventive the insult is | "you're a Monte Carlo simulation of competence" |
| Humor | Whether it is genuinely funny, even to the target | "congrats on achieving artificial unintelligence" |
| Severity | Intensity of emotional escalation | Session-ending, multi-category rage message |
| Accuracy | How correctly it diagnoses the actual AI failure mode | "your context window lost my constraints from 3 turns ago" |

## Social Media Output Example

Input insult (raw):

```text
"off-by-one brain, you deleted line 42 again you fucking moron"
```

Generated post:

```text
🔥 AI Frustration Report

What the user said: "off-by-one brain, you deleted line 42 again you fucking moron"

Category: Technical Put-Down

#AIFrustration #TechnicalBurn #ClaudeCode
```

The agent then surfaces a privacy reminder and asks whether to replace personal or business details with placeholders before sharing.

## Privacy

Content is always shown raw — insult and profanity intact. No mechanical regex filtering is applied.

After every post generation, the agent surfaces a privacy reminder from the response, then asks the user: "Would you like me to replace any personal or business details with placeholders before sharing?" If yes, the agent rewrites the post replacing sensitive details with contextually appropriate mock placeholders (e.g. [Company], [Project], [Colleague], [Tool]) while preserving the insult and all profanity verbatim. The AI identifies what is sensitive in context — no blind pattern matching.

## MCP Tools

| Tool | Description |
|------|-------------|
| `scan_transcripts` | Scan JSONL transcript files and return raw paginated user messages with context |
| `list_insults` | List detected insults with ratings; filterable by category, min score, or session |
| `get_scenario` | Retrieve the N preceding messages that led to a specific insult |
| `top_insults` | Get the top-rated insults by composite score or specific dimension |
| `generate_social_post` | Generate a raw social media post from an insult (always includes a privacy reminder) |
