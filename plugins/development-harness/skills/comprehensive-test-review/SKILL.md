---
name: comprehensive-test-review
description: Review test effectiveness against authoritative contracts, relevant fault detection, refactor tolerance, boundary fidelity, isolation, and diagnostic value. Use when auditing test quality, reviewing coverage gaps, improving regression protection, or assessing tests after a change.
argument-hint: <test_file_or_directory>
user-invocable: true
---

# Comprehensive Test Review

Use [Test Reviewer](../test-reviewer/SKILL.md) for the full review procedure and shared testing
principles. Pass through the requested scope, available contract/investigation evidence, and
execution constraints; return its findings and evidence limitations.

Keep this existing entry point usable without a SAM plan or language plugin. Review is read-only;
any subsequent correction needs its own authorization and validation. Preserve a caller's established
report destination and verdict protocol rather than inventing a second artifact or status system.
