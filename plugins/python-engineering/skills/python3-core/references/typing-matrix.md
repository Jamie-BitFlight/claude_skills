# Python Version & Typing Strategy Matrix

## Lane A: Python 3.10 (constrained / stdlib-only)

```python
from typing import TypeAlias, Protocol, TypeGuard, Literal
from dataclasses import dataclass

# Boundary: json.loads → TypedDict or manual validation
```

## Lane B: Python 3.11+ (stdlib-only)

```python
from typing import TypeAlias, TypeVar, TypedDict, NotRequired, Self, TypeGuard
from enum import StrEnum

# Self for fluent APIs
# assert_type() in tests
# reveal_type() during refactoring
# tomllib for config
```

## Lane C: Python 3.11+ (with Pydantic)

```python
from pydantic import BaseModel, TypeAdapter, Field

class IncomingPayload(BaseModel):
    user_id: int
    email: str
    model_config = {"strict": True}

# TypeAdapter for ad-hoc validation
# validators and serializers
```

## Lane D: Python 3.11+ (with Hypothesis)

```python
from hypothesis import given, strategies as st

@given(st.from_type(IncomingPayload))
def test_payload_validates_round_trip(payload: IncomingPayload) -> None:
    raw = payload.model_dump()
    restored = IncomingPayload.model_validate(raw)
    assert restored == payload
```

## Lane E: Python 3.12

```python
# type statement for explicit aliases
type JSONValue = str | int | float | bool | None | list[JSONValue] | dict[str, JSONValue]

# PEP 695 generic syntax
type Point[T] = tuple[T, T]
```

## Lane F: Python 3.13

```python
from typing import TypeIs, ReadOnly

# TypeIs for bidirectional narrowing (replaces TypeGuard)
def is_str_list(val: list[object]) -> TypeIs[list[str]]:
    return all(isinstance(x, str) for x in val)

# ReadOnly in TypedDict for immutable post-validation fields
```

## Lane G: Python 3.14

- Deferred evaluation of annotations (PEP 649)
- `annotationlib.get_annotations()` for runtime inspection
- Template strings (PEP 750)

## Selection Priority

```
detected python floor ≥ 3.14 → Lane G
detected python floor ≥ 3.13 → Lane F
detected python floor ≥ 3.12 → Lane E
detected python floor ≥ 3.11 + pydantic + hypothesis → Lane D
detected python floor ≥ 3.11 + pydantic → Lane C
detected python floor ≥ 3.11 → Lane B
detected python floor = 3.10 → Lane A
```
