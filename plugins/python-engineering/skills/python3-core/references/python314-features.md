Features added in Python 3.14 (released October 7, 2025). Available when `requires-python >= '3.14'`. For 3.13 additions, see `python313-features.md`.

**Python 3.14 is the current stable release (released October 7, 2025). All features listed are final.**

## Type System

### Deferred annotation evaluation — forward references work without quotes (PEP 649 & PEP 749)

Annotations no longer evaluated eagerly. Forward references no longer need quoting. New `annotationlib` module: `get_annotations()` with `VALUE`, `FORWARDREF`, `STRING` formats.

```python
# 3.14 — forward reference works at definition time
class Node:
    children: list[Node]  # no NameError

# Pre-3.14 — quoting required
class Node:
    children: "list[Node]"
```

Introspecting annotations:

```python
from annotationlib import get_annotations, Format
def func(arg: Undefined): ...
get_annotations(func, format=Format.FORWARDREF)  # {'arg': ForwardRef('Undefined')}
get_annotations(func, format=Format.STRING)       # {'arg': 'Undefined'}
```

### `typing.Union` and `types.UnionType` unified (PEP 749)

`Union[int, str]` and `int | str` now create instances of the same runtime type. Use `==` not `is` to compare. `isinstance(x, typing.Union)` now works.

### `TypeAliasType` supports star unpacking

```python
type Coords[*Ts] = tuple[*Ts]
```

## Template Strings (PEP 750)

### `t""` — Template string literals

`t`-prefix strings return `string.templatelib.Template` (not `str`). Exposes static strings and `Interpolation` objects separately — enables safe SQL, HTML, structured logging, DSLs.

```python
from string.templatelib import Interpolation

tmpl = t"Hello {name}!"
# type(tmpl) == string.templatelib.Template — NOT a str

def render_upper(tmpl):
    return "".join(
        str(p.value).upper() if isinstance(p, Interpolation) else p for p in tmpl
    )
```

No pre-3.14 equivalent — required third-party libraries.

## Stdlib Additions

### `annotationlib` — Annotation introspection (PEP 749)

New stdlib module. Key: `get_annotations(obj, format=Format.VALUE|FORWARDREF|STRING)`.

### `compression` package + `compression.zstd` — Zstandard support (PEP 784)

New `compression` package re-exports `lzma`, `bz2`, `gzip`, `zlib`. New `compression.zstd` adds fast Zstandard compression. Zstd added to `tarfile`, `zipfile`, `shutil`.

```python
from compression import zstd
compressed = zstd.compress(b"data " * 100)
```

### `concurrent.interpreters` — Sub-interpreter stdlib API (PEP 734)

True multi-core parallelism in one process (like `multiprocessing` but stays in-process). Was C-API only before 3.14. `concurrent.futures.InterpreterPoolExecutor` also added.

```python
import concurrent.interpreters
interp = concurrent.interpreters.create()
```

### `pathlib.Path` — Recursive copy/move methods

```python
Path("./data").copy(Path("./backup"))         # recursive copy
Path("./data").copy_into(Path("./archives"))  # copy into dir
Path("./data").move(Path("./new_loc"))        # recursive move
```

Pre-3.14: `shutil.copytree()` / `shutil.move()`.

### Other stdlib additions

- **`pathlib.Path.info`** — `p.info.is_file()` / `p.info.is_dir()` with cached `stat()` results
- **`functools.Placeholder`** — reserve positional slots in `partial()`: `partial(f, Placeholder, "red")`
- **`asyncio` introspection** — `python -m asyncio ps <PID>` / `pstree <PID>`; `asyncio.capture_call_graph()`
- **`inspect.signature()`** — new `annotation_format=Format.STRING` parameter

## Runtime and Concurrency

### Free-threaded Python officially supported (PEP 779)

Free-threaded mode (`python3.14t`) is no longer experimental — it is officially supported in 3.14. The GIL can be disabled at runtime with `-X gil=0`. This was experimental in 3.13.

### Disallow control flow exiting `finally` blocks (PEP 765)

`return`, `break`, and `continue` statements that would exit a `finally` block now emit `SyntaxWarning` (will become `SyntaxError` in a future version). These silently swallowed exceptions in prior versions.

```python
# 3.14 — SyntaxWarning (will be SyntaxError later)
try:
    raise ValueError
finally:
    return 42  # WARNING: silently swallows ValueError
```

## Deprecations and Removals (Architecturally Relevant)

### REMOVED: `asyncio.get_event_loop()` implicit creation

Now raises `RuntimeError` when no current event loop exists. Replace with `asyncio.run(main())`.

### REMOVED: `asyncio` child watcher API

`AbstractChildWatcher`, `FastChildWatcher`, `MultiLoopChildWatcher`, `get/set_child_watcher()` removed (deprecated since 3.12).

### REMOVED: Legacy `ast` node classes

`ast.Bytes`, `ast.Ellipsis`, `ast.NameConstant`, `ast.Num`, `ast.Str` removed. Use `ast.Constant` and `visit_Constant`.

### REMOVED: `itertools` copy/pickle support (deprecated since 3.12)

### DEPRECATED: `asyncio` policy system (removal in Python 3.16)

`get_event_loop_policy()`, `set_event_loop_policy()`, `AbstractEventLoopPolicy` deprecated. Use `asyncio.run()` or `asyncio.Runner(loop_factory=...)`.

### DEPRECATED: `asyncio.iscoroutinefunction()` (removal in Python 3.16) — use `inspect.iscoroutinefunction()`

### DEPRECATED: `codecs.open()` — use built-in `open()`

### Language: `except` without brackets (PEP 758)

```python
# 3.14 — parentheses optional when no `as` clause
except TimeoutError, ConnectionRefusedError:
    ...
```

## `typing_extensions` Backports

`typing_extensions` backports partial `annotationlib` for Python < 3.14: `Format` enum and `get_annotations()`. Note in spec: "Import from `typing_extensions` until `requires-python >= '3.14'`."

## Working Examples

See `.claude/worktrees/video1_python_314/code_python_3_14/` for runnable demos:

- `demo7_t_string.py`, `demo8_t_String_sql.py` — t-string rendering and SQL injection prevention
- `demo9_basic_type_annotation.py` through `demo12_*` — deferred annotation evaluation
- `demo13_circular_ref*.py` — circular imports resolved by deferred annotations
- `demo13_free_threading.py` — GIL-disabled parallel CPU-bound tasks
- `demo14_sub_interpreters.py`, `demo15_interpreter_pool_executor.py` — sub-interpreter concurrency
- `demo4_zstd_lib.py` — gzip vs zstd compression comparison

SOURCE: <https://github.com/devnomial/video1_python_314>

## SOURCE

Python 3.14 What's New (<https://docs.python.org/3.14/whatsnew/3.14.html>, accessed 2026-03-23), Python 3.14.3 Release (<https://www.python.org/downloads/release/python-3143/>, accessed 2026-03-23)
