# Typing-Boundary Policy

## Universal Rules (all lanes)

1. `Any`, broad `object`, and unchecked `cast()` are **forbidden** in normal internal code
2. They are **allowed only** at explicit system boundaries where unknown-shape external data enters
3. Boundary code must live in **dedicated** validator, parser, adapter, or boundary modules
4. Boundary code must **immediately validate and convert** raw input into strongly typed internal objects
5. If Pydantic is available, prefer Pydantic models or `TypeAdapter`
6. If Hypothesis is available, boundary validation should include property-based tests
7. Boundary modules may be the **only** place with narrow lint exceptions for `Any`
8. The typed core must **not** receive raw unvalidated payloads

## Approved Boundary Module Names

Files containing `Any` must be named:

- `*_boundary.py`
- `*_validator.py`
- `*_parser.py`
- `*_adapter.py`
- `*_inbound.py`
- `*_external.py`
- `*_coerce.py`

Or live in directories named `boundary/`, `validators/`, `parsers/`, `adapters/`, `external/`.

## Boundary Wrapper Naming

- `parse_*` — convert raw input to typed object
- `validate_*` — check input meets constraints, return typed result or raise
- `decode_*` — decode serialized format to typed object
- `coerce_*` — force input into correct type with coercion rules
- `*_from_raw` — factory from raw data

## Example: stdlib boundary

```python
# boundary/parser.py
from typing import TypedDict, NotRequired, TypeAlias
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


def parse_incoming(data: object) -> IncomingPayload:
    """Validate an unknown external value and convert it to the typed core."""
    if not isinstance(data, dict):
        raise TypeError("incoming payload must be an object")
    user_id = data.get("user_id")
    email = data.get("email")
    metadata = data.get("metadata", {})
    if not isinstance(user_id, int) or isinstance(user_id, bool):
        raise TypeError("user_id must be an integer")
    if not isinstance(email, str):
        raise TypeError("email must be a string")
    if not isinstance(metadata, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()):
        raise TypeError("metadata must map strings to strings")
    return IncomingPayload(user_id=user_id, email=email, metadata=metadata)
```

## Example: Pydantic boundary

```python
# boundary/validator.py
from pydantic import BaseModel, Field


class IncomingPayload(BaseModel):
    user_id: int
    email: str = Field(pattern=r"^[\w.-]+@[\w.-]+\.\w+$")
    metadata: dict[str, str] = {}
    model_config = {"strict": True}


def validate_incoming(data: dict[str, object]) -> IncomingPayload:
    """Validate raw dict with Pydantic."""
    return IncomingPayload.model_validate(data)
```

## Lint Configuration

```toml
# pyproject.toml
[tool.ruff.lint.per-file-ignores]
"**/boundary/*.py" = ["ANN401"]  # Allow Any only in boundary modules
"**/parsers/*.py" = ["ANN401"]
"**/validators/*.py" = ["ANN401"]
"**/adapters/*.py" = ["ANN401"]
```
