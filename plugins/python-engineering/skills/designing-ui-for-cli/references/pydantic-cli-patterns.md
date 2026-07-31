# Pydantic v2 CLI Patterns

Pydantic v2 patterns relevant to CLI tool development. All content verified against official docs
(accessed 2026-05-07).

SOURCE: <https://docs.pydantic.dev/latest/>
SOURCE: <https://docs.pydantic.dev/latest/concepts/pydantic_settings/>
SOURCE: <https://docs.pydantic.dev/latest/concepts/fields/>
SOURCE: <https://docs.pydantic.dev/latest/concepts/validators/>
SOURCE: <https://docs.pydantic.dev/latest/concepts/serialization/>
SOURCE: <https://docs.pydantic.dev/latest/concepts/strict_mode/>
SOURCE: <https://docs.pydantic.dev/latest/concepts/models/>
SOURCE: <https://github.com/pydantic/pydantic-settings/blob/main/docs/index.md>

---

## pydantic-settings — BaseSettings for CLI config

`pydantic-settings` is a separate package (`pip install pydantic-settings`). It provides
`BaseSettings`, which automatically reads field values from environment variables, dotenv files,
and optionally CLI arguments. It was part of pydantic v1 core but moved to a separate package in
v2.

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MYAPP_",  # reads MYAPP_API_KEY, MYAPP_DATABASE_URL, etc.
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    api_key: str = Field(description="API authentication key")
    database_url: str = Field(default="sqlite:///data.db")
    debug: bool = Field(default=False)
    max_retries: int = Field(default=3, ge=1, le=10)


config = AppConfig()  # reads MYAPP_API_KEY etc. from environment automatically
```

Field value priority from highest to lowest: CLI arguments, `__init__` keyword arguments,
environment variables, dotenv file, secrets directory, field defaults.

To enable parsing of `sys.argv[1:]` as CLI arguments, pass `_cli_parse_args=True` to the
constructor or set it via `SettingsConfigDict`:

```python
# Accept CLI args at runtime
config = AppConfig(_cli_parse_args=True)
```

`AliasChoices` supports multiple environment variable names for a single field:

```python
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_dsn: str = Field(
        default="redis://localhost:6379/0", validation_alias=AliasChoices("service_redis_dsn", "redis_url")
    )
```

SOURCE: <https://github.com/pydantic/pydantic-settings/blob/main/docs/index.md>

---

## ValidationError formatting for CLI stderr output

`ValidationError.errors()` returns a list of dicts. Each dict has keys: `loc` (tuple of field
path components), `msg` (human-readable message), `type` (machine-readable error code), `input`
(the invalid value), and `url` (link to error docs).

`ValidationError.error_count()` returns the number of errors.

```python
from pydantic import BaseModel, ValidationError
import sys


def format_validation_errors(exc: ValidationError) -> str:
    lines = []
    for error in exc.errors(include_url=False):
        location = " -> ".join(str(loc) for loc in error["loc"])
        lines.append(f"  {location}: {error['msg']} (got {error['input']!r})")
    return f"{exc.error_count()} validation error(s):\n" + "\n".join(lines)


try:
    task = TodoTask.model_validate(raw_data)
except ValidationError as exc:
    print(format_validation_errors(exc), file=sys.stderr)
    raise SystemExit(1)
```

`loc` is a tuple of strings and integers. Integers indicate list indices. To produce dot-separated
paths from nested models:

```python
def loc_to_str(loc: tuple) -> str:
    path = ""
    for i, x in enumerate(loc):
        if isinstance(x, str):
            path += ("." if i > 0 else "") + x
        elif isinstance(x, int):
            path += f"[{x}]"
    return path
```

Pass `include_url=False` to `errors()` to omit the `url` key from output shown to users.

SOURCE: <https://docs.pydantic.dev/latest/concepts/models/#error-handling>

---

## FilePath and DirectoryPath for CLI path arguments

Pydantic v2 provides `FilePath` and `DirectoryPath` as path types that validate existence at
validation time. `FilePath` requires the path to exist and be a file. `DirectoryPath` requires the
path to exist and be a directory. Plain `Path` accepts any path string without existence checks.

```python
from pydantic import BaseModel, FilePath, DirectoryPath
from pathlib import Path


class ProcessingArgs(BaseModel):
    input_file: FilePath  # ValidationError if file does not exist
    output_dir: DirectoryPath  # ValidationError if directory does not exist
    log_file: Path  # any path — no existence check (output may not exist yet)


# Typical CLI usage
try:
    args = ProcessingArgs(input_file=cli_args.input, output_dir=cli_args.output, log_file=cli_args.log)
except ValidationError as exc:
    print(format_validation_errors(exc), file=sys.stderr)
    raise SystemExit(1)
```

Use `Path` for output paths that do not yet exist. Use `FilePath`/`DirectoryPath` only for inputs
that must already exist.

SOURCE: <https://docs.pydantic.dev/latest/api/pydantic/standard_library_types/>

---

## computed_field for derived properties

`@computed_field` marks a `@property` as a field that appears in `model_dump()`,
`model_dump_json()`, and the JSON schema (in serialization mode). Without `@computed_field`, a
`@property` is invisible to serialization.

```python
from pydantic import BaseModel, computed_field
from datetime import datetime


class TodoTask(BaseModel):
    title: str
    created_at: datetime
    completed_at: datetime | None = None

    @computed_field
    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    @computed_field
    @property
    def age_days(self) -> int:
        return (datetime.now() - self.created_at).days


task = TodoTask(title="Buy milk", created_at=datetime(2026, 5, 1))
print(task.model_dump())
# {"title": "Buy milk", "created_at": ..., "completed_at": None,
#  "is_complete": False, "age_days": 6}
```

Computed fields are read-only. They cannot be set during initialization. The `@property` decorator
must appear directly below `@computed_field` — the order matters.

SOURCE: <https://docs.pydantic.dev/latest/concepts/fields/#the-computed_field-decorator>

---

## BeforeValidator and AfterValidator — Annotated pattern

`BeforeValidator` runs before Pydantic's type coercion (receives raw input as-is).
`AfterValidator` runs after coercion (receives the typed, coerced value). Both are used inside
`Annotated` metadata to create reusable type aliases.

When applied to a `list[CleanTag]`, the validator runs on each element, not on the list as a
whole. The `@field_validator` decorator approach applies to the entire field value.

```python
from typing import Annotated
from pydantic import AfterValidator, BeforeValidator, BaseModel


def strip_and_lower(v: str) -> str:
    return v.strip().lower()


def non_empty(v: str) -> str:
    if not v:
        raise ValueError("must not be empty")
    return v


# Reusable type alias — strip/lower before coercion, enforce non-empty after
CleanTag = Annotated[str, BeforeValidator(strip_and_lower), AfterValidator(non_empty)]


class TodoTask(BaseModel):
    tags: list[CleanTag]  # validator applied per element, not to the whole list


task = TodoTask(tags=["  Work  ", "PERSONAL"])
print(task.tags)  # ["work", "personal"]
```

Multiple validators in a single `Annotated` type run left-to-right.

SOURCE: <https://docs.pydantic.dev/latest/concepts/validators/#field-validators>

---

## model_dump(exclude_unset=True, exclude_none=True) for partial updates

`model_dump()` by default includes all fields including those set to their default values.
`exclude_unset=True` returns only fields that were explicitly provided during construction —
fields left at their defaults are omitted. `exclude_none=True` excludes any field whose value is
`None` regardless of whether it was set.

The two flags serve different purposes: `exclude_unset=True` distinguishes "not provided" from
"set to default", which is essential when building PATCH-style payloads where omitting a field
means "do not change this field".

```python
from pydantic import BaseModel
from typing import Optional


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[list[str]] = None


# User explicitly provided only title
update = TaskUpdate(title="New title")

update.model_dump()
# {"title": "New title", "priority": None, "tags": None}

update.model_dump(exclude_unset=True)
# {"title": "New title"}  — priority and tags were not set, so omitted

update.model_dump(exclude_none=True)
# {"title": "New title"}  — same result here, but semantics differ:
# a field set explicitly to None would be excluded

update.model_dump(mode="json", exclude_unset=True)
# JSON-safe primitives, same key filtering
```

SOURCE: <https://docs.pydantic.dev/latest/concepts/serialization/#excluding-and-including-fields-based-on-their-value>

---

## PrivateAttr for non-serialised state

`PrivateAttr` declares instance attributes that are excluded from validation, serialization,
`model_dump()`, and JSON schema. They must be initialized in `model_post_init()` or with a
`default`/`default_factory`.

```python
from pydantic import BaseModel, PrivateAttr
from datetime import datetime


class CachedTask(BaseModel):
    title: str
    created_at: datetime

    _cache: dict = PrivateAttr(default_factory=dict)
    _fetch_count: int = PrivateAttr(default=0)

    def model_post_init(self, __context) -> None:
        # Called after __init__ — use for side-effectful initialization
        self._cache = {}

    def get_related(self) -> list:
        self._fetch_count += 1
        return self._cache.get("related", [])


task = CachedTask(title="x", created_at=datetime.now())
task.model_dump()  # {"title": "x", "created_at": ...} — _cache and _fetch_count absent
```

Private attributes are not accessible from outside the model via the `__fields__` or
`model_fields` mappings.

SOURCE: <https://docs.pydantic.dev/latest/concepts/models/#private-model-attributes>

---

## Strict mode

By default, Pydantic coerces input values to the declared type (e.g. `"42"` becomes `42` for an
`int` field). Strict mode disables this coercion and raises a `ValidationError` if the input type
does not exactly match.

Strict mode can be applied at three levels:

Model-wide via `ConfigDict(strict=True)`:

```python
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True)
    id: int
    name: str
    count: int = Field(strict=False)  # override: lax for this one field
```

Per-field via `Field(strict=True)`:

```python
class PartiallyStrict(BaseModel):
    id: int = Field(strict=True)  # "123" raises ValidationError
    name: str  # lax by default — coercion allowed
```

Per-call via `model_validate(..., strict=True)`:

```python
# Validate a specific payload strictly without changing the model
m = MyModel.model_validate({"id": 1, "name": "x"}, strict=True)
```

For CLI tools, strict mode on ID fields and flag fields prevents silent coercion of wrong-type
inputs that arrive as strings from argument parsers. Apply it selectively — strict mode on string
fields that receive user input will break most CLI workflows since all CLI input arrives as `str`.

SOURCE: <https://docs.pydantic.dev/latest/concepts/strict_mode/>
