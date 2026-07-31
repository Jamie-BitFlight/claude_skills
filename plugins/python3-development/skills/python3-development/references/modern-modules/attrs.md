---
title: 'attrs: Python Classes Without Boilerplate'
library_name: attrs
pypi_package: attrs
category: dataclasses
python_compatibility: 3.9+
last_updated: '2025-11-02'
official_docs: https://www.attrs.org
official_repository: https://github.com/python-attrs/attrs
maintenance_status: active
---

# attrs: Python Classes Without Boilerplate

## Core Purpose

attrs eliminates the drudgery of implementing object protocols (dunder methods) by automatically generating `__init__`, `__repr__`, `__eq__`, `__hash__`, and other common methods. It predates Python's built-in dataclasses (which was inspired by attrs) and offers more features and flexibility.

**What problem does it solve?**

- Removes repetitive boilerplate code for class definitions
- Provides declarative attribute definitions with validation and conversion
- Offers slots, frozen instances, and performance optimizations
- Enables consistent, correct implementations of comparison and hashing

**This prevents "reinventing the wheel" by:**

- Auto-generating special methods that are error-prone to write manually
- Providing battle-tested validators and converters
- Handling edge cases in equality, hashing, and immutability correctly
- Offering extensibility through field transformers and custom setters

## Official Information

- **Repository**: <https://github.com/python-attrs/attrs> (@source: python-attrs/attrs on GitHub)
- **PyPI Package**: `attrs` (current version: 25.4.0) (@source: <https://pypi.org/project/attrs/>)
- **Documentation**: <https://www.attrs.org/> (@source: official docs)
- **License**: MIT
- **Maintenance**: Active development, trusted by NASA for Mars missions since 2020 (@source: attrs README)

## Python Version Compatibility

- **Minimum**: Python 3.9+ (@source: PyPI metadata)
- **Maximum**: Python 3.14 (tested and supported)
- **PyPy**: Fully supported
- **Feature notes**:
  - Supports slots by default in modern API (`@define`)
  - Works with all mainstream Python versions including PyPy
  - Implements cell rewriting for `super()` calls in slotted classes
  - Compatible with `functools.cached_property` on slotted classes

## Installation

```bash
pip install attrs
```

For serialization/deserialization support:

```bash
pip install attrs cattrs
```

## Core Usage Patterns

### 1. Basic Class Definition (Modern API)

```python
from attrs import define, field


@define
class Point:
    x: int
    y: int


# Automatically generates __init__, __repr__, __eq__, etc.
p = Point(1, 2)
print(p)  # Point(x=1, y=2)
print(p == Point(1, 2))  # True
```

(@source: Context7 /python-attrs/attrs documentation, attrs README)

### 2. Default Values and Factories

```python
from attrs import define, field, Factory


@define
class SomeClass:
    a_number: int = 42
    list_of_numbers: list[int] = Factory(list)


# Factory prevents mutable default gotchas
sc1 = SomeClass()
sc2 = SomeClass()
sc1.list_of_numbers.append(1)
print(sc2.list_of_numbers)  # [] - separate instances
```

(@source: attrs README, Context7 documentation examples)

### 3. Validators

```python
from attrs import define, field, validators


@define
class User:
    email: str = field(validator=validators.matches_re(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"))
    age: int = field(validator=[validators.instance_of(int), validators.ge(0), validators.lt(150)])


# Custom validator with decorator
@define
class BoundedValue:
    x: int = field()
    y: int

    @x.validator
    def _check_x(self, attribute, value):
        if value >= self.y:
            raise ValueError("x must be smaller than y")
```

(@source: Context7 /python-attrs/attrs validators documentation)

### 4. Converters

```python
from attrs import define, field, converters


@define
class C:
    x: int = field(converter=int)


c = C("42")
print(c.x)  # 42 (converted from string)


# Optional converter
@define
class OptionalInt:
    x: int | None = field(converter=converters.optional(int))


OptionalInt(None)  # Valid
OptionalInt("42")  # Converts to 42
```

(@source: Context7 /python-attrs/attrs converters documentation)

### 5. Frozen (Immutable) Classes

```python
from attrs import frozen, field


@frozen
class Coordinates:
    x: int
    y: int


c = Coordinates(1, 2)
# c.x = 3  # Raises FrozenInstanceError


# Post-init with frozen classes
@frozen
class FrozenWithDerived:
    x: int
    y: int = field(init=False)

    def __attrs_post_init__(self):
        # Must use object.__setattr__ for frozen classes
        object.__setattr__(self, "y", self.x + 1)
```

(@source: Context7 /python-attrs/attrs frozen documentation)

### 6. Slots for Performance

```python
from attrs import define


# Slots enabled by default with @define
@define
class SlottedClass:
    x: int
    y: int


# More memory efficient, faster attribute access
# Cannot add attributes not defined in class
```

(@source: Context7 /python-attrs/attrs slots documentation, attrs glossary)

### 7. Without Type Annotations

```python
from attrs import define, field


@define
class NoAnnotations:
    a_number = field(default=42)
    list_of_numbers = field(factory=list)
```

(@source: attrs README)

## Real-World Examples

### Example Projects Using attrs

1. **Black** - The uncompromising Python code formatter

   - Repository: <https://github.com/psf/black>
   - Usage: Extensive use of attrs for AST node classes (@source: GitHub search)

2. **cattrs** - Composable custom class converters

   - Repository: <https://github.com/python-attrs/cattrs>
   - Usage: Built on top of attrs for serialization/deserialization (@source: python-attrs/cattrs)

3. **Eradiate** - Radiative transfer model
   - Repository: <https://github.com/eradiate/eradiate>
   - Usage: Scientific computing with validated data structures (@source: GitHub code search)

### Common Patterns from Real Code

**Pattern 1: Deep validation for nested structures**

```python
from attrs import define, field, validators


@define
class Measurement:
    tags: dict = field(
        validator=validators.deep_mapping(
            key_validator=validators.not_(validators.in_({"id", "time", "source"}), msg="reserved tag key"),
            value_validator=validators.instance_of((str, int)),
        )
    )
```

(@source: Context7 /python-attrs/attrs deep_mapping validator documentation)

**Pattern 2: Custom comparison for special types**

```python
import numpy as np
from attrs import define, field, cmp_using


@define
class ArrayContainer:
    data: np.ndarray = field(eq=cmp_using(eq=np.array_equal))
```

(@source: Context7 /python-attrs/attrs comparison documentation)

**Pattern 3: Hiding sensitive data in repr**

```python
from attrs import define, field


@define
class User:
    username: str
    password: str = field(repr=lambda value: "***")


User("admin", "secret123")
# Output: User(username='admin', password=***)
```

(@source: Context7 /python-attrs/attrs examples)

## Integration Patterns

### With cattrs for Serialization

```python
from attrs import define
from cattrs import structure, unstructure


@define
class Person:
    name: str
    age: int


# Serialize to dict
data = unstructure(Person("Alice", 30))
# {'name': 'Alice', 'age': 30}

# Deserialize from dict
person = structure({"name": "Bob", "age": 25}, Person)
```

(@source: python-attrs/cattrs repository, Context7 cattrs documentation)

### Field Transformers for Advanced Use Cases

```python
from attrs import define, frozen, field
from datetime import datetime


def auto_convert_datetime(cls, fields):
    results = []
    for f in fields:
        if f.converter is not None:
            results.append(f)
            continue
        if f.type in {datetime, "datetime"}:
            converter = lambda d: datetime.fromisoformat(d) if isinstance(d, str) else d
        else:
            converter = None
        results.append(f.evolve(converter=converter))
    return results


@frozen(field_transformer=auto_convert_datetime)
class Event:
    name: str
    timestamp: datetime


# Automatically converts ISO strings to datetime
event = Event(name="deploy", timestamp="2025-10-21T10:00:00")
```

(@source: Context7 /python-attrs/attrs field_transformer documentation)

## When to Use attrs

### Use attrs when

- You want more features than dataclasses provide
- You need robust validation and conversion
- You require frozen/immutable instances with complex post-init
- You want extensibility (field transformers, custom setters)
- You need to support Python 3.9+ with modern features
- Performance matters (slots optimization)
- You want better debugging experience (cell rewriting for super())
- You prefer a mature, battle-tested library (used by NASA)

### Use dataclasses when

- You need stdlib-only solution (no dependencies)
- Your use case is simple (basic data containers)
- You don't need validators or converters
- You're comfortable with limited customization
- You only support Python 3.10+ (for slots with super())

### Use Pydantic when

- You need runtime type validation (attrs validates on-demand)
- You're building APIs with automatic schema generation
- You need JSON Schema / OpenAPI integration
- You want coercion-heavy validation (Pydantic is more aggressive)
- You need ORM-like features

## Decision Matrix

| Feature            | attrs               | dataclasses   | Pydantic              |
| ------------------ | ------------------- | ------------- | --------------------- |
| **Validators**     | Extensive           | Manual only   | Automatic + extensive |
| **Converters**     | Built-in            | Manual only   | Automatic coercion    |
| **Slots**          | Default in @define  | 3.10+ only    | Optional              |
| **Frozen**         | Full support        | Basic support | Via Config            |
| **Performance**    | Fast (slots)        | Fast          | Slower (validation)   |
| **Type coercion**  | Opt-in              | No            | Automatic             |
| **Dependencies**   | Zero                | Zero (stdlib) | Multiple              |
| **Extensibility**  | High (transformers) | Limited       | Medium                |
| **Python support** | 3.9+                | 3.7+          | 3.8+                  |
| **Schema export**  | Via cattrs          | No            | Built-in              |
| **API stability**  | Very stable         | Stable        | Evolving              |

(@source: Context7 /python-attrs/attrs comparison with dataclasses, research from comparison articles)

## When NOT to Use

1. **Simple data containers without validation**

   - If you just need `__init__` and `__repr__`, dataclasses suffice
   - Example: Simple config objects, DTOs without business logic

2. **When you need JSON Schema / OpenAPI integration**

   - Pydantic provides this out-of-the-box
   - attrs requires additional libraries (cattrs + schema generators)

3. **Heavy runtime type validation requirements**

   - Pydantic validates automatically; attrs requires explicit validators
   - If every field needs type checking at runtime, Pydantic is more convenient

4. **No external dependencies allowed**

   - Use dataclasses from stdlib
   - Though attrs has zero dependencies itself

5. **Working with ORMs requiring specific metaclasses**
   - Some ORMs conflict with attrs' class generation
   - Check compatibility before adopting

## Performance Characteristics

- **Slots**: Enabled by default in `@define`, reducing memory overhead (~40-50% less memory)
- **Frozen classes**: Slightly slower instantiation due to immutability checks
- **Validation**: Only runs when explicitly called via `attrs.validate()` or during `__init__`
- **Comparison**: Generated methods are as fast as hand-written equivalents

(@source: Context7 /python-attrs/attrs performance benchmarks)

## Common Gotchas

1. **Mutable defaults**: Always use `Factory` for mutable defaults
2. **Frozen post-init**: Must use `object.__setattr__` in `__attrs_post_init__`
3. **Slots and dynamic attributes**: Cannot add attributes not defined in class
4. **Pickling slotted classes**: Attributes with `init=False` must be set before pickling
5. **Validator order**: Converters run before validators

(@source: Context7 /python-attrs/attrs documentation, glossary)

## Migration Path

### From dataclasses to attrs

```python
# Before (dataclass)
from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int = 0


# After (attrs)
from attrs import define


@define
class Point:
    x: int
    y: int = 0
```

Minimal changes required; attrs is largely a drop-in replacement with more features.

### From Pydantic to attrs

```python
# Before (Pydantic)
from pydantic import BaseModel, validator


class User(BaseModel):
    name: str
    age: int

    @validator("age")
    def check_age(cls, v):
        if v < 0:
            raise ValueError("age must be positive")
        return v


# After (attrs + cattrs for serialization)
from attrs import define, field, validators


@define
class User:
    name: str
    age: int = field(validator=[validators.instance_of(int), validators.ge(0)])
```

Note: Pydantic does automatic validation; attrs requires explicit calls.

## Additional Resources

- **Official Tutorial**: <https://www.attrs.org/en/stable/examples.html>
- **Extensions**: <https://github.com/python-attrs/attrs/wiki/Extensions-to-attrs>
- **Comparison with dataclasses**: <https://www.attrs.org/en/stable/why.html#data-classes>
- **attrs-strict**: Runtime type validation extension (@source: attrs wiki)
- **Stack Overflow tag**: `python-attrs`

## Conclusion

attrs is the mature, feature-rich choice for defining classes in Python. It predates dataclasses, offers significantly more functionality, and maintains excellent performance through slots optimization. Choose attrs when you need validators, converters, extensibility, or when building production systems requiring robust data structures. It's the foundation used by major projects like Black and is trusted by NASA for critical missions.

For simple cases, dataclasses may suffice. For API validation and schema generation, Pydantic excels. But for general-purpose class definition with powerful features and minimal dependencies, attrs is the gold standard.

---

**Research methodology**: Information gathered from official documentation (attrs.org), PyPI metadata, GitHub repository analysis, Context7 code examples, and comparison with alternative libraries. All sources are cited inline with @ references.
