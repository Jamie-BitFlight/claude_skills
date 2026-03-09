# rtfp — Read The Fucking Prompt

Scans Claude Code session transcripts to find the strongest user reactions to instruction-following
failures, reconstructs the assistant output that triggered them, and turns the best exchange into
a shareable terminal-style artifact.

## Why This Exists

You gave Claude instructions. Clear ones. And at some point it ignored them, and you had a reaction.

RTFP finds that moment. It pulls the assistant output that caused it, the task you were working on,
and your exact reply — and renders them as a shareable image.

It doesn't analyze your session. It doesn't build a report. It finds one exchange and renders it.

## Installation

Add the marketplace (one-time setup):

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
```

Install the plugin:

```bash
/plugin install rtfp@jamie-bitflight-skills
```

## Usage

In any Claude Code session:

```bash
/rtfp
```

Claude will show you a numbered list of available sessions, ask which one to inspect, scan it,
and render the PNG. No other steps required.

## What You Get

### Terminal output

```text
task:      writing a Claude Code plugin
claude:    Validation Error Severity Guide
           1 (Critical): Missing required fields...
           2 (High): Invalid path references...
user:      I LITERALLY just said no scoring. what the fuck

PNG written: rtfp_artifact.png
```

### The PNG

A dark terminal-style image styled after the Claude Code interface:

- Title bar: "rtfp — Read The Fucking Prompt" with red/yellow/green window dots
- `task:` — one dry line describing what you were working on
- `claude:` — the assistant output that triggered the reaction
- `user:` — your reply, in vivid color

<!-- Example PNG: rtfp_example.png (not yet available) -->

Built for sharing. Drop it in a Slack channel, a PR comment, or a post.

## Requirements

- Claude Code v2.0+
- Python 3.11+ (via `uv`)
- At least one Claude Code session transcript on your machine (generated automatically during
  normal use)
