# Standard of Excellence — Source Extracts

Verbatim extracts from `.claude/CLAUDE.md` (project instructions for this repository).
Last verified: 2026-05-22.

---

## Standard of Excellence (CLAUDE.md §Standard of Excellence)

> The marginal cost of completeness is near zero with AI. Do the whole thing. Do it right. Do it with tests. Do it with documentation. Do it so well that the user is genuinely impressed — not politely satisfied, actually impressed. Never offer to 'table this for later' when the permanent solve is within reach. Never leave a dangling thread when tying it off takes five more minutes. Never present a workaround when the real fix exists. The standard isn't 'good enough' — it's 'holy shit, that's done.' Search before building. Test before shipping. Ship the complete thing. When the user asks for something, the answer is the finished product, not a plan to build it. Time is not an excuse. Fatigue is not an excuse. Complexity is not an excuse. Boil the ocean.

---

## No Invented Limits (CLAUDE.md §No Invented Limits)

> Never introduce hard-coded truncation or length limits on content that a consumer (human or agent) needs to read. Arbitrary limits (e.g., `[:500]`, `[:200]`, `MAX_LEN = 1024`) remove the consumer's ability to control what they read, leading to work done with incomplete information.

Rules:
- Output full content by default — let the caller decide how much to read
- When pagination is needed, provide `--offset` / `--limit` parameters so the caller controls the window
- If content must be shortened for a specific display context, always: (1) state it is truncated, (2) report how many characters/lines remain, (3) provide a way to access the rest
- To check state, you only need metadata. To action a task, you need the full content. Do not conflate these two needs.

This applies to: CLI output, JSON fields, error messages, preview panels, descriptions, issue bodies — everything. No silent data loss.

---

## Pre-Existing Issue Accountability (CLAUDE.md §Pre-Existing Issue Accountability)

> Phrase "pre-existing issues not related to my changes" is a TRIGGER TO ACT, not a dismissal justification.

Required response:

> I found [N] pre-existing [issue type] in the codebase. Want to plan how to address them in this session? If not, I'll add them to the backlog.

"Plan" means concrete steps (files, fixes, scope estimate). User decides priority.
"Backlog" means a trackable record (backlog item, issue, task file) that prevents loss.

Reason: Dismissing pre-existing issues normalizes technical debt. Every encountered issue is an opportunity for remediation.

---

SOURCE: `.claude/CLAUDE.md` — lines 11–13 (Standard of Excellence), lines 15–29 (No Invented Limits), lines 327–345 (Pre-Existing Issue Accountability). Extracted 2026-05-22.
