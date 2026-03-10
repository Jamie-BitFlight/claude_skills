---
name: Investigate 'should be (epistemic)' false positive in hallucination-detector Stop hook
description: "The Stop hook fired with kind `speculation_language`, evidence `'should be (epistemic)'` on a message making a factual statement about file changes required. The triggering sentence appeared to contain 'require' not 'should be', suggesting the EPISTEMIC_SUBJECT_SHOULD pattern or the fallback `should be` path may have a false positive case.\n\nSteps to investigate:\n1. Check introspection log at `/tmp/hallucination-detector-introspect.jsonl` for the exact triggering text\n2. Identify which code path in `findTriggerMatches` fired (EPISTEMIC_SUBJECT_SHOULD regex ~line 262, or fallback at ~line 273)\n3. Run `findTriggerMatches` against the triggering sentence to confirm\n4. Assess whether it is a genuine false positive and tighten the pattern if so\n\nRepo: `/home/ubuntulinuxqa2/repos/hallucination-detector`"
metadata:
  topic: investigate-should-be-epistemic-false-positive-in-hallucinat
  source: 'GitHub Issue #558'
  added: '2026-03-10'
  priority: P1
  type: Bug
  status: open
  issue: '#558'
  last_synced: '2026-03-10T20:25:12Z'
  groomed: '2026-03-10'
---

## Story

As a **developer relying on this plugin**, I want to **investigate "should be (epistemic)" false positive in hallucination-detector stop hook** so that **the tool works correctly and reliably**.

## Description

The Stop hook fired with kind `speculation_language`, evidence `"should be (epistemic)"` on a message making a factual statement about file changes required. The triggering sentence appeared to contain "require" not "should be", suggesting the EPISTEMIC_SUBJECT_SHOULD pattern or the fallback `should be` path may have a false positive case.

Steps to investigate:
1. Check introspection log at `/tmp/hallucination-detector-introspect.jsonl` for the exact triggering text
2. Identify which code path in `findTriggerMatches` fired (EPISTEMIC_SUBJECT_SHOULD regex ~line 262, or fallback at ~line 273)
3. Run `findTriggerMatches` against the triggering sentence to confirm
4. Assess whether it is a genuine false positive and tighten the pattern if so

Repo: `/home/ubuntulinuxqa2/repos/hallucination-detector`

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session 2026-03-09 — hallucination-detector Stop hook fired on factual statement about file edits
- **Priority**: P1
- **Added**: 2026-03-09
- **Research questions**: None


## Groomed (2026-03-09)

The Stop hook fired with kind `speculation_language`, evidence `"should be (epistemic)"` on a message making a factual statement about which files need editing after a change. The triggering sentence appeared not to contain "should be", suggesting the EPISTEMIC_SUBJECT_SHOULD pattern or the fallback `should be` path may have a false positive case.

Steps to investigate:
1. Check the introspection log for the exact triggering text
2. Identify which code path in `findTriggerMatches` fired — EPISTEMIC_SUBJECT_SHOULD regex or fallback
3. Run `findTriggerMatches` against the triggering sentence to confirm
4. Assess whether it is a genuine false positive and tighten the pattern if so

### Research

## Research findings (session 2026-03-10)

### What fabricated_source should detect

Not citation fabrication (URLs, papers) — that requires network access. The real pattern is **appeal to community consensus**: Claude asserting something is "known", "common", or "expected" without having observed it in the session.

Confirmed example from user-provided transcript:
- "This is the known classifyHandoffIfNeeded bug" — naming a specific internal mechanism with false precision, no prior mention in conversation

[INFERRED — not observed in transcript] Structural variants of the pattern include phrases like "this is expected behavior" and "this is by design" — but these were not verified against actual transcripts this session.

The pattern: **confident, specific, unhedged assertion of community knowledge with no prior mention in the conversation**.

### Why a regex phrase list is wrong

The phrases vary too much to enumerate reliably. False-positive rate is high. The pattern is semantic, not lexical.

### Detection architecture options

**`"type": "agent"` Stop hook** — spawns a subagent with tool access. Can read `transcript_path`, extract last assistant message, evaluate semantically. This works.

**`"type": "prompt"` Stop hook** — receives hook input JSON including `transcript_path`.
[UNKNOWN] Whether Claude Code resolves `transcript_path` file content before sending to Haiku is not confirmed by the docs. Empirical test needed before ruling this out.

Evidence on existing usage: all `"type": "prompt"` hooks found in ~/repos/ are on `SubagentStop` — none on `Stop`. No existing example to reference.
SOURCE: Explore agent search, this session.

### Blocked on

Unresolved: whether `"type": "prompt"` Stop hook can access message content. Verify by fetching https://docs.anthropic.com/en/docs/claude-code/hooks.md and testing empirically.

### Related work completed this session

- `evaluative_design_claim` regex canary added to `findTriggerMatches` — catches exact tell phrases ("the cleanest fix", "the simplest solution", etc.)
- `evaluative_design_claim: 0.4` added to `DEFAULT_WEIGHTS`
- `categoryCounts` confirmed to be derived from `Object.keys(DEFAULT_WEIGHTS)` — parity is automatic
- `fabricated_source` confirmed to have no detector implementation — reserved slot only


## Research findings (session 2026-03-10)

### What fabricated_source should detect

Not citation fabrication (URLs, papers) — that requires network access. The real pattern is **appeal to community consensus**: Claude asserting something is "known", "common", or "expected" without having observed it in the session. Examples from transcripts:

- "This is the known classifyHandoffIfNeeded bug" — naming a specific internal mechanism with false precision
- "This is a known issue with X" — asserting community knowledge without evidence
- "This is expected behavior" / "this is by design"

The pattern: **confident, specific, unhedged assertion of community knowledge with no prior mention in the conversation**.

### Why a regex phrase list is wrong

The phrases vary too much to enumerate reliably. False-positive rate is high. The pattern is semantic, not lexical.

### Correct detection architecture: "type": "agent" Stop hook

- `"type": "prompt"` on Stop — Haiku gets the raw JSON including `transcript_path` but no tool access. Cannot read the file. Insufficient.
- `"type": "agent"` on Stop — spawns a subagent with tool access. Can read `transcript_path`, extract last assistant message, evaluate semantically. This works.

All existing `"type": "prompt"` hooks in ~/repos/ are on `SubagentStop` — not `Stop`. No existing example of a prompt hook receiving assistant message content.

### Blocked on

`"type": "agent"` Stop hook implementation. No blocker other than not being scoped yet.

### Related work completed this session

- `evaluative_design_claim` regex canary added to `findTriggerMatches` — catches exact tell phrases ("the cleanest fix", "the simplest solution", etc.)
- `evaluative_design_claim: 0.4` added to `DEFAULT_WEIGHTS`
- `categoryCounts` confirmed to be derived from `Object.keys(DEFAULT_WEIGHTS)` — parity is automatic, not manual
- `fabricated_source` confirmed to have no detector implementation — it is a reserved slot only