# Testing Standards

## Test Naming

Behavioral naming: `test_{function}_{scenario}_{expected_result}`

```python
def test_validate_email_with_invalid_format_raises_validation_error() -> None:
    """Validate that malformed emails are rejected."""
    ...
```

## AAA Pattern

```python
def test_user_registration() -> None:
    # Arrange
    user_data = {"email": "test@example.com", "name": "Test"}
    service = UserService(repository)

    # Act
    result = service.register(user_data)

    # Assert
    assert result.success is True
    assert repository.count() == 1
```

## Fixture Hierarchy

```text
conftest.py (root)
├── Session fixtures (db connections, servers)
├── Module fixtures (shared test data)
└── Function fixtures (isolated per-test data)

tests/
├── conftest.py              # Shared fixtures
├── unit/
│   └── conftest.py          # Unit-specific fixtures
└── integration/
    └── conftest.py          # Integration-specific fixtures
```

## Exception Testing

```python
def test_validation_error() -> None:
    """Test validation raises ValueError for invalid input."""
    with pytest.raises(ValueError, match="Invalid email format"):
        validate_email("not-an-email")
```

## Coverage Configuration

```toml
[tool.coverage.run]
branch = true
source = ["src"]
omit = ["**/tests/**", "**/__pycache__/**"]

[tool.coverage.report]
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```
