---
title: "Utilization Proposals: claude-replay"
---

## Utilization 1: transcript-analysis skill → claude-replay CLI

**Research entry**: ./research/coding-agents/claude-replay.md
**Caller**: ./plugins/agentskill-kaizen/skills/transcript-analysis/SKILL.md
**Integration mechanism**: CLI subprocess
**Replaces or adds**: Adds capability to generate shareable interactive session replays for analysis findings
**Setup cost**: Low (npm install only)
**Integration surface**: `claude-replay <session-id> -o replay.html` with optional `--redact`, `--turns`, `--theme` flags

### Why this caller

The transcript-analysis skill processes Claude Code JSONL session transcripts and writes findings to markdown reports (`.planning/kaizen/analysis-DATE.md`). When the analysis identifies significant patterns — anti-patterns, inefficiencies, frustration signals, or workflow innovations — the findings reference specific session IDs but lack a way to make those sessions navigable for stakeholders. claude-replay transforms referenced session IDs into interactive HTML replays that let users step through the exact turns where the pattern occurred, understand agent reasoning, and verify findings contextually. This bridges the gap between textual analysis findings and empirical evidence.

The skill already knows session locations (`~/.claude/projects/{project-key}/{uuid}.jsonl`) and could batch-generate replays for all sessions analyzed in a kaizen run, with optional filtering (`--turns N-M`) to focus on the problematic turns identified in the analysis.

### Integration sketch

```bash
#!/bin/bash
# After transcript-analysis completes, generate replays for referenced sessions

SESSION_ID="abc123def456"
OUTPUT_DIR=".planning/kaizen/replays/"

# Generate replay from session ID
claude-replay "$SESSION_ID" \
  -o "$OUTPUT_DIR/session-$SESSION_ID.html" \
  --theme dracula \
  --redact-api-keys

# If analysis flagged turns 10-25 as problematic, focus the replay
claude-replay "$SESSION_ID" \
  --turns 10-25 \
  -o "$OUTPUT_DIR/session-$SESSION_ID-focused.html" \
  --title "Anti-pattern Example: $FINDING_NAME" \
  --redact-api-keys
```

Kaizen reports could link to generated replays: `[View session replay](./replays/session-abc123-focused.html)` for each analyzed finding.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| linear-walkthrough skill (`./.claude/skills/linear-walkthrough/SKILL.md`) | Walkthrough skill produces architectural documentation and codebase exploration guides. While it could theoretically embed example replays as teaching aids, the skill's output is markdown-based structured codebase analysis, not interactive demos. Embedding replays would require architectural changes to the synthesis agent and output format. No direct overlap with integration surface — the skill does not invoke or interact with session transcripts. |
| plugin-creator/skill-creator skill (`./plugins/plugin-creator/skills/skill-creator/SKILL.md`) | Skill-creator produces new skill directory structures and SKILL.md files. Could theoretically generate a replay of a successful skill-creation session for onboarding, but no direct API integration surface exists. Would require wrapper script or hook to orchestrate replay generation post-completion. Not a tight fit for the skill's primary responsibility (skill scaffolding). |

---

## Notes

**claude-replay version**: 0.4.0 (latest, released 2026-03-13)

**Browser compatibility**: Decompression requires Chrome 80+, Firefox 113+, Safari 16.4+. For older browsers, the `--no-compress` flag disables compression but increases file size 3-4x. This is acceptable for internal/private use cases.

**Secret redaction**: Automatic by default (enabled via research entry). The transcript-analysis skill should verify that generated replays do not contain API keys, database credentials, or other secrets before storing them in shared directories. claude-replay's `--no-auto-redact` flag should never be used in automated context.

**Privacy**: Generated HTML files embed the full session transcript (compressed). The research entry documents this explicitly. Kaizen analysis should not generate replays for sessions containing proprietary algorithms, business logic, or sensitive data without explicit approval from stakeholders.
