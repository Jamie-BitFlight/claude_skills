---
name: python3-typing
description: Selects and applies the strongest valid Python typing strategy for the current project. Use when designing models, validating external data, addressing type checker failures, reducing Any usage, defining boundaries, or choosing between stdlib typing, Pydantic, and Hypothesis-based boundary testing.
user-invocable: false
---

# Python Typing

Choose the strongest valid lane automatically. Do not ask the user to pick a typing philosophy.

Consult `references/typing-policy.md` for the full policy document.

## Required Policy

- Forbid `Any`, broad `object`, and unchecked `cast()` in normal internal code
- Allow them only at explicit boundaries where unknown-shape data enters
- Isolate boundary code in dedicated validator, parser, adapter, or boundary modules
- Validate immediately and return strongly typed internal objects
- Do not let raw payloads cross into the typed core
- Allow narrow lint exceptions for `Any` only in approved boundary modules

## Lane Selection

### 1. Python 3.10 Constrained or stdlib-only

- Use only compatibility-safe stdlib typing features
- Prefer `dataclasses`, `TypedDict`, `Protocol`, `Literal`, `TypeGuard`, `NewType`
- Validate with explicit runtime checks in dedicated boundary wrappers
- No third-party type assumptions

### 2. Python 3.11+ stdlib-only

- Use modern stdlib typing features supported by the interpreter
- Use `Self`, `assert_type`, and `reveal_type` where useful during refactoring
- `TypedDict` with `NotRequired`

### 3. Python 3.11+ with Pydantic

- Use Pydantic models for ingress contracts
- Prefer strict mode where coercion would hide upstream errors
- Use `TypeAdapter` for annotated types that do not need full models
- See `references/pydantic-boundaries.md`

### 4. Python 3.11+ with Hypothesis

- Property-test boundaries, validators, parsers, and invariants
- Prefer `from_type()` where practical
- See `references/hypothesis-boundaries.md`

### 5. Python 3.12+

- Use `type` statement for explicit type aliases: `type JSONValue = str | int | ...`
- Use PEP 695 generic parameter syntax for new generic helpers

### 6. Python 3.13+

- Use `TypeIs` for clearer custom narrowing helpers (replaces `TypeGuard` where bidirectional narrowing needed)
- Use `ReadOnly` in `TypedDict` fields that must not mutate after validation

### 7. Python 3.14+

- Keep annotation-reading infrastructure compatible with deferred evaluation (PEP 649)
- Use `annotationlib.get_annotations()` in infrastructure that inspects annotations at runtime

## Boundary Implementation Standard

Use dedicated wrappers named like:

- `parse_*`
- `validate_*`
- `decode_*`
- `coerce_*`
- `*_from_raw`

Boundary modules should return typed objects only.

### Example: stdlib-only boundary

```python
from typing import TypedDict, NotRequired
from dataclasses import dataclass

class _RawIncoming(TypedDict):
    user_id: int
    email: str
    metadata: NotRequired[dict[str, str]]

@dataclass(frozen=True, slots=True)
class IncomingPayload:
    user_id: int
    email: str
    metadata: dict[str, str]

def parse_incoming(data: _RawIncoming) -> IncomingPayload:
    return IncomingPayload(
        user_id=data["user_id"],
        email=data["email"],
        metadata=data.get("metadata", {}),
    )
```

### Example: Pydantic boundary

```python
from pydantic import BaseModel, TypeAdapter

class IncomingPayload(BaseModel):
    user_id: int
    email: str
    metadata: dict[str, str] = {}
    model_config = {"strict": True}

def parse_incoming(data: dict[str, object]) -> IncomingPayload:
    return IncomingPayload.model_validate(data)
```

## References

- `references/typing-policy.md` — full boundary validation policy
- `references/pydantic-boundaries.md` — Pydantic model and TypeAdapter patterns
- `references/hypothesis-boundaries.md` — property-based testing for validators
