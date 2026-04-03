# Hypothesis Boundary Testing Patterns

## Property-Based Tests for Validators

```python
from hypothesis import given, strategies as st
from pydantic import BaseModel

class Point(BaseModel):
    x: float
    y: float
    model_config = {"strict": True}

@given(st.from_type(Point))
def test_point_validates_round_trip(point: Point) -> None:
    raw = point.model_dump()
    restored = Point.model_validate(raw)
    assert restored == point
```

## Round-Trip for Parsers/Serializers

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_sort_preserves_length(data: list[int]) -> None:
    result = sorted(data)
    assert len(result) == len(data)

@given(st.text(min_size=1))
def test_encode_decode_round_trip(text: str) -> None:
    encoded = encode(text)
    decoded = decode(encoded)
    assert decoded == text
```

## from_type() Where Practical

```python
from hypothesis import given, strategies as st

@given(st.from_type(int))
def test_validator_accepts_all_ints(value: int) -> None:
    result = validate_int(value)
    assert result == value
```

## Custom Strategies

```python
from hypothesis import strategies as st
from typing import TypedDict

class Record(TypedDict):
    name: str
    age: int

record_strategy = st.builds(
    Record,
    name=st.text(min_size=1, max_size=100),
    age=st.integers(min_value=0, max_value=150),
)
```
