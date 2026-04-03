# Design Standards

## SOLID Principles (Active Guidance)

### Single Responsibility
Each module/class has one reason to change.

### Open/Closed
Open for extension, closed for modification. Use Protocols and composition.

### Liskov Substitution
Subtypes must be substitutable for base types without breaking behavior.

### Interface Segregation
Clients should not depend on interfaces they don't use. Prefer small Protocols.

### Dependency Inversion
Depend on abstractions (Protocols), not concretions. Use dependency injection.

## Module Structure

```text
project/
├── pyproject.toml
├── README.md
├── src/
│   └── my_package/
│       ├── __init__.py      # Public API surface (__all__)
│       ├── cli.py           # CLI layer (Typer commands)
│       ├── core.py          # Business logic
│       ├── services.py      # External service integrations
│       ├── models.py        # Domain models
│       ├── boundary/        # Validation (only place for Any)
│       │   ├── __init__.py
│       │   ├── parser.py
│       │   └── validator.py
│       └── types.py         # Type aliases and Protocols
└── tests/
    ├── conftest.py
    ├── unit/
    ├── integration/
    └── boundary/            # Tests for boundary validation
```

## Error Handling Pattern

```python
def get_user(id: str) -> User:
    try:
        return db.query(User, id)
    except ConnectionError:
        logger.warning("DB unavailable, using cache")
        return cache.get(f"user:{id}")  # Specific recovery
```

## Protocol-Based DI

```python
from typing import Protocol

class Repository(Protocol):
    def get(self, id: str) -> User: ...
    def save(self, user: User) -> None: ...

def create_user(repo: Repository, data: UserInput) -> User:
    user = User(**data)
    repo.save(user)
    return user
```
