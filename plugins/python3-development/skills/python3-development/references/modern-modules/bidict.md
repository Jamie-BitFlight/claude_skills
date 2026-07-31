---
title: 'bidict: Bidirectional Mapping Library'
library_name: bidict
pypi_package: bidict
category: data-structures
python_compatibility: 3.9+
last_updated: '2025-11-02'
official_docs: https://bidict.readthedocs.io
official_repository: https://github.com/jab/bidict
maintenance_status: active
---

# bidict: Bidirectional Mapping Library

## Overview

bidict provides efficient, Pythonic bidirectional mapping data structures for Python. It allows you to maintain a one-to-one mapping between keys and values where you can look up values by keys and keys by values with equal efficiency.

## Official Information

- **Repository**: @[https://github.com/jab/bidict]
- **Documentation**: @[https://bidict.readthedocs.io]
- **PyPI Package**: `bidict`
- **Latest Stable Version**: 0.23.1 (February 2024)
- **Development Version**: 0.23.2.dev0
- **License**: MPL-2.0 (Mozilla Public License 2.0)
- **Maintenance**: Actively maintained since 2009 (15+ years)
- **Author**: Joshua Bronson (@jab)
- **Stars**: 1,554+ on GitHub

## Python Version Compatibility

- **Minimum Required**: Python 3.9+
- **Tested Versions**: 3.9, 3.10, 3.11, 3.12, PyPy
- **Python 3.13/3.14**: Expected to be compatible (no version-specific blockers)
- **Type Hints**: Fully type-hinted codebase

Source: @[pyproject.toml line 9: requires-python = ">=3.9"]

## Core Purpose

### The Problem bidict Solves

bidict eliminates the need to manually maintain two separate dictionaries when you need bidirectional lookups. Without bidict, you might be tempted to:

```python
# DON'T DO THIS - The naive approach
mapping = {"H": "hydrogen", "hydrogen": "H"}
```

**Problems with this approach:**

- Unclear distinction between keys and values when iterating
- `len()` returns double the actual number of associations
- Updating associations requires complex cleanup logic to avoid orphaned data
- No enforcement of one-to-one invariant
- Iterating `.keys()` also yields values, and vice versa

### What bidict Provides

```python
from bidict import bidict

# The correct approach
element_by_symbol = bidict({"H": "hydrogen"})
element_by_symbol["H"]  # 'hydrogen'
element_by_symbol.inverse["hydrogen"]  # 'H'
```

bidict maintains two separate internal dictionaries and keeps them automatically synchronized, providing:

- **One-to-one invariant enforcement**: Prevents duplicate values
- **Automatic inverse synchronization**: Changes propagate bidirectionally
- **Clean iteration**: `.keys()` returns only keys, `.values()` returns only values
- **Accurate length**: `len()` returns the actual number of associations
- **Type safety**: Fully typed for static analysis

Source: @[docs/intro.rst: "to model a bidirectional mapping correctly and unambiguously, we need two separate one-directional mappings"]

## When to Use bidict

### Use bidict When

1. **Bidirectional lookups are required**

   - Symbol-to-element mapping (H ↔ hydrogen)
   - User ID-to-username mapping
   - Code-to-description mappings
   - Translation dictionaries between two systems

2. **One-to-one relationships must be enforced**

   - Database primary key mappings
   - File path-to-identifier mappings
   - Token-to-user session mappings

3. **You need both directions with equal frequency**

   - The overhead of two dicts is justified by lookup patterns
   - Inverse lookups are not occasional edge cases

4. **Data integrity is important**
   - Automatic cleanup when updating associations
   - Protection against duplicate values via `ValueDuplicationError`
   - Fail-clean guarantees for bulk operations

### Use Two Separate Dicts When

1. **Inverse lookups are rare or never needed**

   - Simple one-way mappings
   - Lookups only in one direction

2. **Values are not unique**

   - Many-to-one relationships (multiple keys → same value)
   - Example: category-to-items mapping

3. **Values are unhashable**

   - Lists, dicts, or other mutable/unhashable values
   - bidict requires values to be hashable

4. **Memory is extremely constrained**
   - bidict maintains two internal dicts (approximately 2x memory)
   - For very large datasets where inverse is rarely used

Source: @[docs/intro.rst, docs/basic-usage.rst]

## Decision Matrix

<eg>
┌─────────────────────────────────────┬──────────────┬──────────────────┐
│ Requirement                         │ Use bidict   │ Use Two Dicts    │
├─────────────────────────────────────┼──────────────┼──────────────────┤
│ Bidirectional lookups frequently    │ ✓            │                  │
│ One-to-one constraint enforcement   │ ✓            │                  │
│ Values must be hashable             │ ✓            │                  │
│ Automatic synchronization needed    │ ✓            │                  │
│ Many-to-one relationships           │              │ ✓                │
│ Unhashable values (lists, dicts)    │              │ ✓                │
│ Inverse lookups are rare            │              │ ✓                │
│ Extreme memory constraints          │              │ ✓                │
└─────────────────────────────────────┴──────────────┴──────────────────┘
</eg>

## Installation

```bash
pip install bidict
```

Or with uv:

```bash
uv add bidict
```

No runtime dependencies outside Python's standard library.

## Basic Usage Examples

### Creating and Using a bidict

```python
from bidict import bidict

# Create from dict, keyword arguments, or items
element_by_symbol = bidict({"H": "hydrogen", "He": "helium"})
element_by_symbol = bidict(H="hydrogen", He="helium")
element_by_symbol = bidict([("H", "hydrogen"), ("He", "helium")])

# Forward lookup (key → value)
element_by_symbol["H"]  # 'hydrogen'

# Inverse lookup (value → key)
element_by_symbol.inverse["hydrogen"]  # 'H'

# Inverse is a full bidict, kept in sync
element_by_symbol.inverse["helium"] = "He"
element_by_symbol["He"]  # 'helium'
```

Source: @[docs/intro.rst, docs/basic-usage.rst]

### Handling Duplicate Values

```python
from bidict import bidict, ValueDuplicationError

b = bidict({"one": 1})

# This raises an error - value 1 already exists
try:
    b["two"] = 1
except ValueDuplicationError:
    print("Value 1 is already mapped to 'one'")

# Explicitly allow overwriting with forceput()
b.forceput("two", 1)
# Result: bidict({'two': 1}) - 'one' was removed
```

Source: @[docs/basic-usage.rst: "Values Must Be Unique"]

### Standard Dictionary Operations

```python
from bidict import bidict

b = bidict(H="hydrogen", He="helium")

# All standard dict methods work
"H" in b  # True
b.get("Li", "not found")  # 'not found'
b.pop("He")  # 'helium'
b.update({"Li": "lithium"})  # Add items
len(b)  # 2

# Iteration yields only keys (not keys+values like naive approach)
list(b.keys())  # ['H', 'Li']
list(b.values())  # ['hydrogen', 'lithium']
list(b.items())  # [('H', 'hydrogen'), ('Li', 'lithium')]
```

Source: @[docs/basic-usage.rst: "Interop"]

## Advanced Features

### Other bidict Types

```python
from bidict import frozenbidict, OrderedBidict

# Immutable bidict (hashable, can be dict key or set member)
immutable = frozenbidict({"H": "hydrogen"})

# Ordered bidict (maintains insertion order, like dict in Python 3.7+)
ordered = OrderedBidict({"H": "hydrogen", "He": "helium"})
```

Source: @[docs/other-bidict-types.rst]

### Fine-Grained Duplication Control

```python
from bidict import bidict, OnDup, RAISE, DROP_OLD

b = bidict({1: "one"})

# Strict mode - raise on any key or value duplication
b.put(2, "two", on_dup=OnDup(key=RAISE, val=RAISE))

# Custom policies for different duplication scenarios
on_dup = OnDup(key=DROP_OLD, val=RAISE)
b.putall([(1, "uno"), (2, "dos")], on_dup=on_dup)
```

Source: @[docs/basic-usage.rst: "Key and Value Duplication"]

### Fail-Clean Guarantee

```python
from bidict import bidict

b = bidict({1: "one", 2: "two"})

# If an update fails, the bidict is unchanged
try:
    b.putall({3: "three", 1: "uno"})  # 1 is duplicate key
except KeyDuplicationError:
    pass

# (3, 'three') was NOT added - the bidict remains unchanged
b  # bidict({1: 'one', 2: 'two'})
```

Source: @[docs/basic-usage.rst: "Updates Fail Clean"]

## Real-World Usage Patterns

Based on analysis of the bidict repository and documentation:

### Pattern 1: Symbol-to-Name Mappings

```python
from bidict import bidict

# Chemical elements
element_by_symbol = bidict({"H": "hydrogen", "He": "helium", "Li": "lithium"})

# Look up element by symbol
element_by_symbol["H"]  # 'hydrogen'

# Look up symbol by element name
element_by_symbol.inverse["lithium"]  # 'Li'
```

### Pattern 2: ID-to-Object Mappings

```python
from bidict import bidict

# User session management
session_by_user_id = bidict({1001: "session_abc123", 1002: "session_def456"})

# Find session by user ID
session_by_user_id[1001]  # 'session_abc123'

# Find user ID by session
session_by_user_id.inverse["session_abc123"]  # 1001
```

### Pattern 3: Internationalization/Translation

```python
from bidict import bidict

# Language code mappings
lang_code = bidict({"en": "English", "es": "Español", "fr": "Français"})

# Look up language name from code
lang_code["es"]  # 'Español'

# Look up code from language name
lang_code.inverse["Français"]  # 'fr'
```

### Pattern 4: File Path-to-Identifier Mappings

```python
from bidict import bidict

# File tracking system
file_by_id = bidict({"f001": "/path/to/document.pdf", "f002": "/path/to/image.png"})

# Get path from ID
file_by_id["f001"]  # '/path/to/document.pdf'

# Get ID from path
file_by_id.inverse["/path/to/image.png"]  # 'f002'
```

## Integration Patterns

### With Type Hints

```python
from typing import Mapping
from bidict import bidict


def process_mapping(data: Mapping[str, int]) -> None:
    # bidict is a full Mapping implementation
    for key, value in data.items():
        print(f"{key}: {value}")


# Works seamlessly
process_mapping(bidict({"a": 1, "b": 2}))
```

### With collections.abc

bidict implements:

- `collections.abc.MutableMapping` (for `bidict`)
- `collections.abc.Mapping` (for `frozenbidict`)

```python
from collections.abc import MutableMapping
from bidict import bidict


def validate_mapping(m: MutableMapping) -> bool:
    return isinstance(m, MutableMapping)


validate_mapping(bidict())  # True
```

### Polymorphic Equality

```python
from bidict import bidict

# bidict compares equal to dicts with same items
bidict(a=1, b=2) == {"a": 1, "b": 2}  # True

# Can convert freely between dict and bidict
dict(bidict(a=1))  # {'a': 1}
bidict(dict(a=1))  # bidict({'a': 1})
```

Source: @[docs/basic-usage.rst: "Interop"]

## Performance Characteristics

### Time Complexity

- **Forward lookup** (`b[key]`): O(1)
- **Inverse lookup** (`b.inverse[value]`): O(1)
- **Insert/Update** (`b[key] = value`): O(1)
- **Delete** (`del b[key]`): O(1)
- **Access inverse** (`b.inverse`): O(1) - inverse is always maintained, not computed on demand

### Space Complexity

- **Memory overhead**: Approximately 2x a single dict (maintains two internal dicts)
- **Inverse access**: No additional memory allocation (inverse is a view)

Source: @[docs/intro.rst: "the inverse is not computed on demand"]

## Known Limitations

1. **Values must be hashable**: Cannot use lists, dicts, or other unhashable types as values
2. **Memory overhead**: Uses roughly 2x the memory of a single dict
3. **One-to-one only**: Cannot represent many-to-one or one-to-many relationships
4. **Value uniqueness enforced**: Raises `ValueDuplicationError` by default when duplicate values are inserted

Source: @[docs/basic-usage.rst: "Values Must Be Hashable", "Values Must Be Unique"]

## When NOT to Use

### Scenario 1: Many-to-One Relationships

```python
# BAD: Multiple keys mapping to same value
# This won't work with bidict - use dict instead
category_to_items = {
    "fruit": "apple",
    "vegetable": "carrot",
    "fruit": "banana",  # Duplicate value for different key
}
```

### Scenario 2: Unhashable Values

```python
# BAD: Lists as values
# This raises TypeError with bidict
groups = bidict({
    "admins": ["alice", "bob"],  # TypeError: unhashable type: 'list'
    "users": ["charlie", "david"],
})

# Use regular dict or use frozenset/tuple as values
groups = bidict({
    "admins": frozenset(["alice", "bob"]),  # OK
    "users": frozenset(["charlie", "david"]),
})
```

### Scenario 3: Rarely Used Inverse Lookups

```python
# If you only need inverse lookup occasionally, manual approach may be simpler
forward = {"key1": "value1", "key2": "value2"}

# Occasionally create inverse when needed
inverse = {v: k for k, v in forward.items()}
```

### Scenario 4: Extreme Memory Constraints

For very large datasets (millions of entries) where inverse lookups are infrequent, the 2x memory overhead may not be justified. Consider:

- Database-backed lookups for both directions
- On-demand inverse dict construction
- External key-value stores with bidirectional indices

## Notable Dependents

bidict is used by major organizations and projects (source: @[README.rst]):

- Google
- Venmo
- CERN
- Baidu
- Tencent

**PyPI Download Statistics**: Significant adoption with millions of downloads (source: @[README.rst badge])

## Dependencies

- **Runtime**: None (zero dependencies outside Python stdlib)
- **Development**: pytest, hypothesis, mypy, sphinx (for testing and docs)

Source: @[pyproject.toml: dependencies = []]

## Maintenance and Support

- **Maintenance**: Actively maintained since 2009 (15+ years)
- **Test Coverage**: 100% test coverage with property-based testing via hypothesis
- **CI/CD**: Continuous testing across all supported Python versions
- **Type Hints**: Fully type-hinted and mypy-strict compliant
- **Documentation**: Comprehensive documentation at readthedocs.io
- **Community**: GitHub Discussions for questions, active issue tracker
- **Enterprise Support**: Available via Tidelift subscription

Source: @[README.rst: "Features", "Enterprise Support"]

## Migration Guide

### From Two Manual Dicts

```python
# Before: Manual synchronization
forward = {"H": "hydrogen"}
inverse = {"hydrogen": "H"}

# When updating
forward["H"] = "hydrogène"
del inverse["hydrogen"]  # Manual cleanup
inverse["hydrogène"] = "H"

# After: Automatic synchronization
from bidict import bidict

mapping = bidict({"H": "hydrogen"})
mapping["H"] = "hydrogène"  # inverse automatically updated
```

### From Naive Single Dict

```python
# Before: Mixed keys and values
mixed = {"H": "hydrogen", "hydrogen": "H"}
len(mixed)  # 2 (wrong - should be 1 association)
list(mixed.keys())  # ['H', 'hydrogen'] (values mixed in)

# After: Clean separation
from bidict import bidict

b = bidict({"H": "hydrogen"})
len(b)  # 1 (correct)
list(b.keys())  # ['H'] (only keys)
list(b.values())  # ['hydrogen'] (only values)
```

## Related Libraries and Alternatives

- **Two manual dicts**: Simplest for occasional inverse lookups
- **bidict.OrderedBidict**: When insertion order matters (built into bidict)
- **bidict.frozenbidict**: Immutable variant for hashable mappings (built into bidict)
- **sortedcontainers.SortedDict**: For sorted bidirectional mappings (can combine with bidict)

No direct competitors in Python stdlib or third-party ecosystem that provide the same level of safety, features, and maintenance.

## Learning Resources

- Official Documentation: @[https://bidict.readthedocs.io]
- Intro Guide: @[https://bidict.readthedocs.io/intro.html]
- Basic Usage: @[https://bidict.readthedocs.io/basic-usage.html]
- Learning from bidict: @[https://bidict.readthedocs.io/learning-from-bidict.html] - covers advanced Python topics touched by bidict's implementation
- GitHub Repository: @[https://github.com/jab/bidict]
- PyPI Package: @[https://pypi.org/project/bidict/]

## Quick Decision Guide

**Use bidict when you answer "yes" to:**

1. Do you need to look up keys by values frequently?
2. Are your values unique (one-to-one relationship)?
3. Are your values hashable?
4. Do you want automatic synchronization between directions?

**Use two separate dicts when:**

1. Inverse lookups are rare
2. You have many-to-one relationships
3. Memory is extremely constrained
4. Values are unhashable

**Use a single dict when:**

1. You only need one direction
2. Values don't need to be unique

## Code Review Checklist

When reviewing code using bidict:

- [ ] Values are hashable (not lists, dicts, sets)
- [ ] One-to-one relationship is intended (no many-to-one)
- [ ] Error handling for `ValueDuplicationError` where appropriate
- [ ] `forceput()`/`forceupdate()` usage is intentional and documented
- [ ] Memory overhead (2x dict) is acceptable for use case
- [ ] Type hints include bidict types where appropriate
- [ ] Inverse access pattern justifies bidict usage vs two dicts

## Summary

bidict is a mature, well-tested library that solves the bidirectional mapping problem elegantly. Use it when you need efficient lookups in both directions with automatic synchronization and one-to-one invariant enforcement. Avoid it when you have many-to-one relationships, unhashable values, or rarely use inverse lookups.

**Key Takeaway**: If you're maintaining two dicts manually or considering `{a: b, b: a}`, reach for bidict. It eliminates error-prone manual synchronization while providing stronger guarantees and cleaner code.
