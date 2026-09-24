---
name: verify-integration
description: Verify that changed components are actually connected into the intended end-to-end system flow. Use when checking imports/exports, registrations, data/control flow, configuration consumption, call paths, and boundary compatibility after implementation.
---
# Verify Integration

Existence is not integration.

1. Establish the intended end-to-end flow and the changed components' expected producers, consumers, registrations, and boundaries.
2. Trace each changed component from its entry or producer through the expected consumer/path.
3. Verify imports/exports, registrations, configuration loading, type/schema compatibility, data transformations, and error propagation where applicable.
4. Prefer executable end-to-end or focused integration evidence when static linkage cannot prove behavior.
5. Identify orphaned outputs, dead registrations, mismatched contracts, incomplete call paths, and paths that exist only in tests/mocks when production wiring is required.
6. Report VERIFIED paths, concrete integration gaps, and unverified boundaries separately.

Do not infer integration from symbol existence, matching names, or lexical references alone.
