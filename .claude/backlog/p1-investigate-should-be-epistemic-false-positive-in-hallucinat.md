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
  last_synced: '2026-03-10T06:55:32Z'
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