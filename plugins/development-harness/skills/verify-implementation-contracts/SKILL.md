---
name: verify-implementation-contracts
description: Compare explicit design/specification contracts with the implementation in a defined change scope. Use to verify signatures, types, schemas, invariants, and other stated contracts without expanding into general code quality review.
---
# Verify Implementation Contracts

Verify only explicit contracts in scope.

1. Identify the authoritative specification and the changed implementation boundary.
2. Extract explicit contracts: interfaces/signatures, parameter/return types, schemas, identifier rules, invariants, or other mechanically observable requirements.
3. Map each contract to the implementation module(s) in the supplied change scope. Skip contracts owned by untouched modules unless the requested verification scope includes them.
4. Inspect the implementation using language-appropriate parsing/reading. Do not treat a failed grep or unsupported language as evidence of absence.
5. Classify an in-scope mismatch as CONTRACT VIOLATION and an explicit required contract with no implementation evidence as CONTRACT GAP.
6. Report expected evidence, actual evidence, precise location, and the mismatch. Report clean only when every in-scope explicit contract has been checked.

Do not infer contracts the specification does not state. Do not review style, design preference, or general correctness unless those are explicit contracts.
