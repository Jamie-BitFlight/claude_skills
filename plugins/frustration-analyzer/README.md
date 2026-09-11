# RTFP — Read The Fucking Prompt

Find the strongest user reaction to an AI instruction-following failure in a Claude or Codex
session, then render the exchange as a shareable terminal-style PNG.

## Installation

```bash
/plugin install frustration-analyzer@jamie-bitflight-skills
```

Or for local testing:

```bash
claude --plugin-dir ./plugins/frustration-analyzer
```

## What It Does

RTFP analyzes a direct session path or a selected set of Claude and Codex sessions:

```text
1. Select sessions
2. Find the strongest reaction
3. Reconstruct the exchange and render a PNG
```

The final artifact contains exactly three things:

1. **task** — a single dry line describing what was being worked on
2. **assistant said** — the assistant output that triggered the reaction
3. **user replied** — the user's exact words

## Quick Start

```text
/rtfp
```

The plugin lists recent Claude or Codex sessions with provider labels, or accepts a date range. A multi-session date-range request runs without a one-session selection prompt.

Or pass a session path directly:

```text
/rtfp ~/.claude/projects/myproject/abc123.jsonl
```

```text
/rtfp ~/.codex/sessions/2026/03/09/rollout-abc123.jsonl
```

Analyze a natural-language range:

```text
/rtfp this week
```

RTFP interprets `this week` in your timezone and shows the exact dates plus the Claude/Codex session counts. If the complete requested set is too large to analyze safely, it asks you to narrow the date range or provider first.

## Example Output

```
┌─ RTFP ──────────────────────────────────────────┐

  task: writing a Claude Code plugin

  assistant:
    Here is a bulleted list of steps:
    - Step 1: Create the SKILL.md file
    - Step 2: Add frontmatter

  user:
    I said no bullets. How are you still doing bullets.

└──────────────────────────────────────────────────┘
```

PNG saved to the run's private output location.

## Privacy

Receipts contain verbatim transcript content and perform no automatic redaction or publishing.
Review and redact details before sharing.

## What This Is Not

- Not a dashboard for your entire history — analyze one session or a selected date range
- Not an insult scorer — no taxonomy, no ratings, no verdicts
- Not a sentiment analyzer — it finds specific instruction-following failures
