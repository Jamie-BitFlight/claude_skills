---
name: Loguru - Python Logging Made Simple
description: Loguru is a drop-in replacement for Python's standard `logging` module that eliminates boilerplate configuration. It provides a single pre-configured global `logger` object that outputs to `stderr`...
license: MIT
metadata:
  topic: loguru
  category: developer-tools
  source_url: https://github.com/loguru
  github: Delgan/loguru
  version: "0.7.3"
  verified: "2026-02-09"
  next_review: "2026-05-09"
---

## Overview

Loguru is a drop-in replacement for Python's standard `logging` module that eliminates boilerplate configuration. It provides a single pre-configured global `logger` object that outputs to `stderr` by default and can be fully reconfigured with a single `add()` call. Zero required dependencies on Linux/macOS (only `colorama` on Windows).

---

## Problem Addressed

| Problem | Loguru Solution |
|---------|----------------|
| stdlib `logging` requires multi-step setup (logger, handler, formatter, filter) | Single `from loguru import logger` with zero configuration needed |
| `%`-style string formatting in log messages is outdated and error-prone | Modern `{}` (str.format) syntax: `logger.info("User {name}", name=user)` |
| File rotation requires `RotatingFileHandler` and manual setup | Built-in `rotation`, `retention`, `compression` parameters on `add()` |
| Thread exceptions are silently dropped by stdlib logging | `@logger.catch` decorator catches and logs errors in threads |
| Exception tracebacks lack variable context | `diagnose=True` shows variable values in tracebacks |
| Datetime formatting uses confusing `datefmt`/`%(asctime)s` patterns | Simple `{time:YYYY-MM-DD HH:mm:ss}` format tokens |
| Structured logging requires third-party libraries | Built-in JSON serialization via `serialize=True` |
| No easy way to add per-request context to log messages | `bind()` and `contextualize()` for structured context injection |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 23,577 | 2026-02-09 |
| GitHub Forks | 766 | 2026-02-09 |
| Open Issues | 250 | 2026-02-09 |
| Subscribers | 137 | 2026-02-09 |
| Repository Created | 2017-08-15 | - |
| Latest Release | 0.7.3 (2024-12-06) | 2026-02-09 |
| Package Size | 61.6 KB (pure Python wheel) | 2026-02-09 |
| Python Support | >=3.5 | 2026-02-09 |
| PEP 561 Typed | Yes (py.typed marker + type stubs) | 2026-02-09 |

---

## Key Features

### Zero-Config Global Logger

```python
from loguru import logger

logger.debug("Works immediately, outputs to stderr")
```

Single `logger` instance, no `getLogger()` needed. Pre-configured with colored stderr output.

### Unified `add()` Function

Replaces Handler + Formatter + Filter with one call. Sinks can be:

- File-like objects (`sys.stderr`)
- File paths (string/Path, with automatic file management)
- Callables (any function accepting a message)
- Coroutine functions (async sinks)
- stdlib `logging.Handler` instances

```python
logger.add("app.log", rotation="500 MB", retention="10 days", compression="gz")
logger.add(sys.stdout, format="{time} {level} {message}", level="INFO")
logger.add(custom_sink_function, serialize=True)
```

### Seven Built-in Log Levels

| Level | Numeric | Note |
|-------|---------|------|
| TRACE | 5 | Below DEBUG, for fine-grained tracing |
| DEBUG | 10 | Standard debug |
| INFO | 20 | Standard info |
| SUCCESS | 25 | Loguru addition, between INFO and WARNING |
| WARNING | 30 | Standard warning |
| ERROR | 40 | Standard error |
| CRITICAL | 50 | Standard critical |

Custom levels via `logger.level("AGENT_STEP", no=25)`.

### Exception Catching

```python
@logger.catch(default=None)
def risky(a, b):
    return a / b


result = risky(10, 0)  # Returns None, error logged with full traceback

with logger.catch(message="Something failed"):
    do_risky_operation()
```

### Structured Logging and Context

```python
# bind() - returns new logger with extra context
child = logger.bind(request_id="abc-123", user="admin")
child.info("Processing")

# contextualize() - context-local via contextvars (thread/async safe)
with logger.contextualize(task_id=42):
    logger.info("In context")  # extra = {'task_id': 42}

# serialize=True - JSON output
logger.add(sink, serialize=True)

# patch() - modify record dict dynamically
logger = logger.patch(lambda r: r["extra"].update(version="1.0"))
```

### Lazy Evaluation

```python
logger.opt(lazy=True).debug("Result: {x}", x=lambda: expensive_computation())
```

Lambda is never called if sink level is above DEBUG.

### Per-Message Configuration via `opt()`

```python
logger.opt(exception=True).info("Log with traceback")
logger.opt(colors=True).info("<blue>colored</blue> message")
logger.opt(record=True).info("Line: {record[line]}")
logger.opt(raw=True).info("Bypass formatting\n")
logger.opt(depth=1).info("Use parent stack frame")
```

### File Rotation, Retention, and Compression

```python
logger.add("app.log", rotation="500 MB")  # Size-based
logger.add("app.log", rotation="12:00")  # Time-based (daily at noon)
logger.add("app.log", rotation="1 week")  # Duration-based
logger.add("app.log", retention="10 days")  # Auto-cleanup old files
logger.add("app.log", compression="gz")  # Compress on rotation
```

### stdlib Compatibility

Three integration patterns:

1. **stdlib Handler as Loguru sink**: `logger.add(syslog_handler)`
2. **Propagate Loguru to stdlib**: Custom `PropagateHandler`
3. **Intercept stdlib into Loguru**: `InterceptHandler` pattern funnels all stdlib logging through Loguru

### Library-Friendly disable/enable

```python
# In library code:
logger.disable("my_library")  # All logging becomes no-op
# In application code:
logger.enable("my_library")  # Re-enable
```

### Environment Variable Configuration

Default stderr handler configurable via: `LOGURU_FORMAT`, `LOGURU_LEVEL`, `LOGURU_DIAGNOSE`, `LOGURU_BACKTRACE`, `LOGURU_COLORIZE`, `LOGURU_SERIALIZE`, `LOGURU_ENQUEUE`, `LOGURU_CATCH`. Also supports `NO_COLOR` and `FORCE_COLOR`.

### Multiprocess-Safe Enqueue

```python
logger.add("file.log", enqueue=True)  # Messages via multiprocessing-safe queue
await logger.complete()  # Wait for all enqueued messages
```

---

## Technical Architecture

### Package Structure

Pure Python package (~200KB, 21 files). No compiled extensions.

| File | Purpose |
|------|---------|
| `_logger.py` (98KB) | Core Logger class -- entire public API |
| `_better_exceptions.py` (22KB) | Enhanced traceback formatting with variable values |
| `_colorizer.py` (15KB) | ANSI color markup processing |
| `_file_sink.py` (14KB) | File sink with rotation/retention/compression |
| `_handler.py` (13KB) | Internal handler bridging logger to sinks |
| `__init__.pyi` (12KB) | Full type stubs (PEP 561) |
| `_datetime.py` (5KB) | Custom datetime formatting |
| `_string_parsers.py` (5KB) | Rotation/retention string expression parsing |
| `_simple_sinks.py` (4KB) | Simple sink implementations |
| `_defaults.py` (3KB) | Default config and environment variable handling |

### Architecture Pattern

Single-instance, handler-dispatch model. `Logger` maintains an internal list of handlers. `add()` creates handlers with specified sink/format/filter/level. Log methods dispatch to all handlers passing level and filter checks. `bind()`, `contextualize()`, `patch()`, `opt()` return lightweight wrapper instances that modify the record without creating separate loggers.

### Rich Record Dict

Every log message carries a record dict:

| Key | Type | Description |
|-----|------|-------------|
| `elapsed` | `timedelta` | Time since program start |
| `exception` | tuple or None | Exception info |
| `extra` | `dict` | Custom context from `bind()`/`contextualize()` |
| `file` | `RecordFile` | Source file (name, path) |
| `function` | `str` | Function name |
| `level` | `RecordLevel` | Level (name, no, icon) |
| `line` | `int` | Line number |
| `message` | `str` | Formatted message text |
| `module` | `str` | Module name |
| `name` | `str` | `__name__` of calling module |
| `process` | `RecordProcess` | Process (id, name) |
| `thread` | `RecordThread` | Thread (id, name) |
| `time` | `datetime` | Timezone-aware timestamp |

---

## Installation and Usage

```bash
# pip
pip install loguru

# uv
uv pip install loguru
uv add loguru

# PEP 723 inline script metadata
# /// script
# dependencies = ["loguru"]
# ///
```

### Quick Start

```python
from loguru import logger

# Remove default handler, add custom one
logger.remove()
logger.add("app.log", rotation="10 MB", retention="7 days", compression="gz")
logger.add(sys.stderr, level="WARNING", colorize=True)

# Log with context
with logger.contextualize(request_id="abc-123"):
    logger.info("Processing request")


# Catch exceptions
@logger.catch
def main():
    process_data()
```

### InterceptHandler Pattern (Unify All Logging)

```python
import logging
import inspect


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            if depth > 0 and not (
                filename == logging.__file__ or ("importlib" in filename and "_bootstrap" in filename)
            ):
                break
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
```

---

## Relevance to Claude Code Development

### Applications

1. **CLI Tool Logging**: Loguru's default stderr output avoids interfering with stdout piping. Environment variable control (`LOGURU_LEVEL=DEBUG`) enables verbose mode without code changes. `NO_COLOR` support follows CLI conventions.

2. **Agent Script Diagnostics**: Python scripts in `plugins/**/scripts/` that use PEP 723 can add `loguru` as a dependency for structured diagnostic output. The `bind()` method enables per-task context (agent name, step number) in log output.

3. **Exception Handling in Hooks**: `@logger.catch` wrapping hook entry points provides automatic error logging with full variable-value tracebacks, replacing silent failures.

4. **Unified Library Logging**: The `InterceptHandler` pattern funnels all stdlib `logging` from third-party libraries (httpx, requests, etc.) through Loguru for consistent formatting and filtering.

### Patterns Worth Adopting

1. **`contextualize()` for Request Tracking**: Agents processing multiple tasks can attach `task_id`, `agent_name`, `model` to all log messages within an async context using `contextvars`.

2. **`serialize=True` for Machine-Readable Logs**: JSON-structured logs with the full record dict enable downstream log analysis and monitoring.

3. **Lazy Evaluation for Debug Logging**: Expensive debug output (serializing large model inputs) can use `opt(lazy=True)` to avoid computation when debug is disabled.

4. **`disable()`/`enable()` for Library Code**: Libraries/plugins can disable their Loguru logging by default, letting the consuming application opt in.

---

## Integration Opportunities

> Auto-generated by research-context-agent. Review before acting.

### Enhances Existing

| Target | Type | How |
|--------|------|-----|
| `plugins/python3-development/skills/python3-development/` | skill | Add Loguru to modern-modules.md reference as a recommended alternative to stdlib logging for CLI scripts, emphasizing zero-config logger and PEP 723 compatibility for scripts needing structured logging with automatic rotation. |
| `plugins/python3-development/skills/shebangpython/` | skill | Include guidance on adding `loguru` to PEP 723 dependency blocks for scripts needing logging with rotation, showing the uv shebang pattern handles dependency installation automatically. |
| `plugins/bash-development/skills/bash-logging/` | skill | Add cross-reference note that Python scripts with PEP 723 can achieve similar structured logging (levels, colors, rotation) using Loguru instead of implementing bash logging functions from scratch. |
| `plugins/python3-development/skills/stinkysnake/` | skill | Add Loguru's `logger.catch` decorator to exception handling best practices section as modern approach for automatic exception logging with full context (replacing manual try-except logging patterns). |

### Cross-References

- Related research: `research/ai-observability/logfire.md` — Logfire is Pydantic's observability platform built on OpenTelemetry for LLM applications; Loguru provides the application-level logging that feeds into observability platforms like Logfire through structured output (`serialize=True` for JSON logs).
- Related research: `research/llm-infrastructure/tensorzero.md` — TensorZero provides LLM gateway observability; Loguru's structured logging with `contextualize()` enables correlation between application logs and TensorZero's LLM traces using shared context IDs (request_id, task_id).

---

## References

1. **Loguru Documentation** - <https://loguru.readthedocs.io> (accessed 2026-02-09)
2. **Loguru GitHub Repository** - <https://github.com/Delgan/loguru> (accessed 2026-02-09)
3. **Loguru README** - <https://raw.githubusercontent.com/Delgan/loguru/master/README.md> (accessed 2026-02-09, via research agent)
4. **GitHub API - Repository Metadata** - <https://api.github.com/repos/Delgan/loguru> (accessed 2026-02-09): stars, forks, license, creation date
5. **GitHub API - Latest Release** - <https://api.github.com/repos/Delgan/loguru/releases/latest> (accessed 2026-02-09): v0.7.3, release notes
6. **Installed Package Metadata** - `importlib.metadata.metadata('loguru')` on loguru 0.7.3: version, license, Python requirement, dependencies
7. **Installed Package Source** - `/usr/local/lib/python3.11/dist-packages/loguru/`: file sizes, architecture, type stubs verified by direct inspection
8. **Installed Package Help** - `help(logger.add)`, `help(logger.catch)`, `help(logger.opt)`, `help(logger.bind)`, `help(logger.contextualize)`: parameter documentation and signatures verified by direct execution
