---
name: non-adr-history
description: Fixture target skill exercising the DELETE (non-ADR) branch. Use when the eval harness needs a skill with rejected-alternative history behind an easily reversible, single-caller decision.
---
# Eval5 Target

## Format output as JSON

Emit the result as JSON. Early drafts of this skill used a CSV output instead, and before that a
plain key=value text format, but both were dropped once the calling agent flagged them as harder
to parse reliably; switching the output format now would be trivial since only one caller reads it
and JSON is a one-line change either direction.
