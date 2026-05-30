# Implicit-Checklist Patterns — Grouped by Partition-Readiness

A typology of implicit checklists found in real instructions, grouped by how cleanly each
pre-partitions into overlapping worker jobs. Use it to recognize a fan-out candidate and to
choose worker boundaries with minimal design effort.

## Table of Contents

- [Group 1 — Named principle set (partition handed to you free)](#group-1--named-principle-set-partition-handed-to-you-free)
- [Group 2 — "modernization / idiomatic / pythonic" (the classic implicit list)](#group-2--modernization--idiomatic--pythonic-the-classic-implicit-list)
- [Group 3 — "review X for quality" (the broadest implicit bucket)](#group-3--review-x-for-quality-the-broadest-implicit-bucket)
- [Group 4 — Prompt-engineering / skill-quality self-review](#group-4--prompt-engineering--skill-quality-self-review)
- [The tell](#the-tell)

---

## Group 1 — Named principle set (partition handed to you free)

When the rubric is a named framework, its own categories ARE the worker boundaries. Near-zero
design work.

- `twelve-factor-app` — literally 12 factors. One worker per factor (or per 3).
- SOLID reviews — 5 principles = 5 overlapping jobs.
- Security review → OWASP categories (injection, authz, secrets, SSRF, deserialization,
  path traversal).
- Accessibility review → WCAG criteria.
- `design-anti-patterns` (the Uncodixfy rule set) → one worker per anti-pattern family.

## Group 2 — "modernization / idiomatic / pythonic" (the classic implicit list)

The rubric is named but unenumerated. Enumerate it once, then split the roster into buckets.

- `modernpython` "look for modernization opportunities" → an explicit PEP roster: 585 generics,
  604 unions, 572 walrus, 634 match, 673 Self, StrEnum, tomllib, pathlib, dataclasses. Each PEP
  is a rule; the roster splits into N buckets.
- `snakepolish` / `review` "pythonic best practices" → comprehensions, context managers, EAFP,
  enumerate/zip, mutable-default-arg, truthiness.

## Group 3 — "review X for quality" (the broadest implicit bucket)

- Generic code review → correctness / error-handling / naming / dead-code / structure as
  separate scenario buckets. This is exactly what `/code-review`'s A/B/C angles already are.
- `comprehensive-test-review` → AAA, isolation, mocking, parametrization, flaky-patterns,
  coverage thresholds.
- Performance review → N+1, blocking-in-hot-path, redundant I/O, allocation.

## Group 4 — Prompt-engineering / skill-quality self-review

This repo eats its own dog food here — these are rule-following skills that review skills/agents.

- `ai-doc-optimizer`, `subagent-refactorer` "apply Anthropic best practices" → positive framing,
  front-loaded constraints, XML tagging, examples-present, no-contradictions — each a checkable rule.
- `audit-skill-completeness` → frontmatter / progressive-disclosure / citations / link-validity /
  token-size.
- `doc-drift-auditor` → each documented claim vs code (already a per-item loop, ideal to fan out).
- `CLAUDE.md` / `.claude/rules` process review → per-rule clarity + cross-rule contradiction detection.

## The tell

Any instruction containing "ensure … follows", "review for", "look for … opportunities", or a
named framework is an implicit checklist. Named frameworks (12-factor, SOLID, WCAG, OWASP, a PEP
set) are **pre-partitioned** — their own categories are the natural overlapping job boundaries,
so those convert with near-zero design work.
