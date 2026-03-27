---
title: Modern Python Modules Reference
description: Comprehensive guide to high-quality, Python 3.11+ compatible modules organized by use case
last_updated: '2025-10-29'
python_compatibility: 3.11+
---

# Modern Python Modules Reference

This reference guide covers high-quality, actively maintained Python modules that are compatible with Python 3.11+ and represent modern best practices. Each module is vetted for production use and includes guidance on when to use it.

## Quick Navigation

- **[Package & Project Management](#package--project-management)** - Dependency management, packaging, and project tooling
- **[CLI Development](#cli-development)** - Building command-line applications
- **[Web Frameworks & APIs](#web-frameworks--apis)** - Web development and API frameworks
- **[HTTP & Network](#http--network)** - HTTP clients, protocols, and networking
- **[Data Processing & Analysis](#data-processing--analysis)** - Data manipulation and analysis
- **[Testing & Quality](#testing--quality)** - Testing frameworks and code quality tools
- **[Async & Concurrency](#async--concurrency)** - Async programming and concurrent execution
- **[Type Checking & Validation](#type-checking--validation)** - Data validation and type safety
- **[Configuration Management](#configuration-management)** - Config handling and secrets
- **[Logging & Monitoring](#logging--monitoring)** - Logging, tracing, and observability
- **[Database & ORM](#database--orm)** - Database drivers and ORM solutions
- **[Data Structures & Utilities](#data-structures--utilities)** - Specialized data structures and utility functions
- **[Serialization](#serialization)** - Data serialization and encoding

---

## Package & Project Management

### uv

**PyPI:** `uv` | **Status:** Active | **Python:** 3.11+

Modern package manager and project tool written in Rust. Replaces pip, pip-tools, pipx, poetry, pyenv, and virtualenv with 10-100x performance improvements.

**Key Features:**

- Blazingly fast dependency resolution and installation
- PEP 723 inline script metadata support
- Single lockfile for reproducible environments
- Python version management built-in
- Virtual environment creation and management

**When to Use:**

- Managing Python projects with modern tooling
- Creating portable scripts with dependencies
- Building CI/CD pipelines
- Replacing Poetry or pip-tools workflows

**See Also:** For comprehensive uv documentation, activate the uv skill: `Skill(skill: "python3-development:uv")`

---

### hatch

**PyPI:** `hatch` | **Status:** Active | **Python:** 3.11+

Modern build backend and project manager. Standardizes Python packaging without configuration complexity.

**Key Features:**

- Reproducible builds via hatch.build
- Built-in test runner and environment management
- Version bumping automation
- Dynamic field support in pyproject.toml

**When to Use:**

- Building and packaging libraries
- Automating version management
- Standardizing project structure

---

## CLI Development

### Click

**PyPI:** `click` | **Status:** Active | **Python:** 3.11+

Elegant and intuitive command-line interface creation framework. Emphasizes composability and convention over configuration.

**Key Features:**

- Automatic help text generation
- Type hints support
- Command composition and nesting
- Custom parameter types
- Shell completion support

**When to Use:**

- Building user-friendly CLI applications
- Creating command-line tools with subcommands
- Rapid prototyping of command-line interfaces

**Related:** Typer (Type-based alternative using Pydantic)

---

### Typer

**PyPI:** `typer` | **Status:** Active | **Python:** 3.11+

Modern CLI framework based on Click but using Python type hints and Pydantic for automatic parsing.

**Key Features:**

- Pure Python type hints (no decorators needed)
- Automatic shell completion
- Built-in help generation
- Pydantic integration for parameter validation
- Intuitive and explicit API

**When to Use:**

- Building type-safe CLIs
- Rapid CLI development with type validation
- Creating Python scripts with structured arguments

**Comparison with Click:**

- Typer emphasizes types and simplicity
- Click is more explicit and composable
- Choose Typer for rapid development, Click for complex nested commands

---

### Rich

**PyPI:** `rich` | **Status:** Active | **Python:** 3.11+

Terminal rendering library for rich text and beautiful formatting in the terminal.

**Key Features:**

- Syntax highlighting for code
- Progress bars and spinners
- Formatted tables and tree displays
- Markup-based text styling
- Console control and automation

**When to Use:**

- Adding attractive output to CLI applications
- Displaying progress in long-running operations
- Creating formatted reports in the terminal
- Building interactive terminal applications

---

### Fabric

**PyPI:** `fabric` | **Status:** Active | **Python:** 3.11+

High-level API for executing shell commands remotely or locally. Built on top of Paramiko.

**Key Features:**

- Execute commands over SSH
- Local command execution
- File transfer (PUT/GET)
- Configurable host lists and task runners
- Context managers for clean command management

**When to Use:**

- Deployment automation
- Remote system administration
- Building deployment scripts
- Task automation across multiple hosts

**See Also:** `modern-modules/fabric.md`

---

## Web Frameworks & APIs

### FastAPI

**PyPI:** `fastapi` | **Status:** Active | **Python:** 3.11+

Modern, fast web framework for building APIs with Python type hints. Built on Starlette and Pydantic.

**Key Features:**

- Automatic OpenAPI/Swagger documentation
- Built-in dependency injection
- Request validation via Pydantic models
- Excellent async/await support
- WebSocket support

**When to Use:**

- Building REST APIs
- Creating high-performance web services
- Building microservices with documentation
- Real-time applications with WebSockets

---

### Starlette

**PyPI:** `starlette` | **Status:** Active | **Python:** 3.11+

Lightweight ASGI framework for building async web applications. Foundation for FastAPI.

**Key Features:**

- ASGI-based async request handling
- Middleware support
- WebSocket support
- Background tasks
- Excellent testing utilities

**When to Use:**

- Lightweight web applications
- ASGI server applications
- Middleware development
- When you need lower-level control than FastAPI

---

### Pydantic

**PyPI:** `pydantic` | **Status:** Active | **Python:** 3.11+

Data validation library using Python type hints. Provides runtime type checking and data parsing.

**Key Features:**

- Runtime type validation
- Automatic type coercion
- JSON Schema generation
- Custom validators
- Serialization support

**When to Use:**

- API request/response validation
- Configuration validation
- Data pipeline validation
- Creating self-documenting data models

---

## HTTP & Network

### httpx

**PyPI:** `httpx` | **Status:** Active | **Python:** 3.11+

Modern HTTP client library with both sync and async support. Designed as next-generation requests replacement.

**Key Features:**

- Synchronous and asynchronous APIs
- HTTP/1.1 and HTTP/2 support
- Type annotations throughout
- Default timeout behavior
- ASGI/WSGI testing support

**When to Use:**

- Building async HTTP clients
- Making HTTP requests with modern Python
- Need both sync and async in one library
- Testing ASGI/WSGI applications

**See Also:** `modern-modules/httpx.md`

---

### requests

**PyPI:** `requests` | **Status:** Maintained | **Python:** 3.11+

Ubiquitous HTTP library for simple, synchronous HTTP requests.

**Key Features:**

- Simple, Pythonic API
- Automatic redirects
- Session management
- Cookie handling
- SSL verification

**When to Use:**

- Simple synchronous HTTP requests
- Legacy project compatibility
- When async support is not needed
- Broad ecosystem compatibility

**Note:** httpx is recommended for new projects requiring async support

---

### aiohttp

**PyPI:** `aiohttp` | **Status:** Active | **Python:** 3.11+

Async HTTP client/server framework. Built for both client and server async HTTP operations.

**Key Features:**

- HTTP server and client
- WebSocket support
- Built-in connection pooling
- Middleware support
- Streaming support

**When to Use:**

- Async HTTP clients with server component
- Building full async web services
- Need built-in WebSocket server support

---

### paho-mqtt

**PyPI:** `paho-mqtt` | **Status:** Active | **Python:** 3.11+

MQTT client library for IoT and message-based applications.

**Key Features:**

- MQTT protocol support
- Synchronous and asynchronous APIs
- TLS/SSL encryption
- Will messages and persistence
- Callbacks for event handling

**When to Use:**

- Building IoT applications
- MQTT message publishing and subscribing
- Integrating with MQTT brokers
- Message-based system communication

**See Also:** `modern-modules/paho-mqtt.md`

---

## Data Processing & Analysis

### Pandas

**PyPI:** `pandas` | **Status:** Active | **Python:** 3.11+

Powerful data manipulation and analysis library. Standard for data science and analytics.

**Key Features:**

- DataFrames for tabular data
- Series for labeled 1D data
- Built-in plotting and visualization integration
- SQL-like operations
- Time series functionality

**When to Use:**

- Data manipulation and cleaning
- Exploratory data analysis
- Building data pipelines
- Working with tabular data

---

### NumPy

**PyPI:** `numpy` | **Status:** Active | **Python:** 3.11+

Fundamental library for numerical computing. Foundation for scientific Python stack.

**Key Features:**

- N-dimensional arrays (ndarray)
- Vectorized operations
- Linear algebra operations
- Random number generation
- FFT capabilities

**When to Use:**

- Numerical computations
- Scientific and mathematical operations
- Foundation for other data science libraries
- Array-based data processing

---

### Polars

**PyPI:** `polars` | **Status:** Active | **Python:** 3.11+

Fast DataFrame library written in Rust with Python bindings. Modern alternative to Pandas for large datasets.

**Key Features:**

- High-performance execution
- Lazy evaluation support
- Memory efficient
- Comprehensive expression API
- Out-of-core processing

**When to Use:**

- Large dataset processing
- Performance-critical data pipelines
- New projects prioritizing speed
- Memory-constrained environments

---

### DuckDB

**PyPI:** `duckdb` | **Status:** Active | **Python:** 3.11+

In-process SQL database engine optimized for analytics workloads.

**Key Features:**

- SQL queries on data files
- Parquet, CSV, and other format support
- Excellent query performance
- Easy Python integration
- No server required

**When to Use:**

- Analytical SQL queries on files
- Data exploration with SQL
- In-process data warehousing
- Replacing complex pandas operations

---

## Testing & Quality

### pytest

**PyPI:** `pytest` | **Status:** Active | **Python:** 3.11+

Mature testing framework with powerful fixtures and plugin system.

**Key Features:**

- Simple test function syntax
- Powerful fixtures for test setup
- Parametrization for multiple test cases
- Excellent assertion introspection
- Rich plugin ecosystem

**When to Use:**

- Writing unit and integration tests
- Any Python project testing
- Standard test framework for projects

---

### pytest-cov

**PyPI:** `pytest-cov` | **Status:** Active | **Python:** 3.11+

Code coverage measurement plugin for pytest.

**Key Features:**

- Coverage reporting with pytest
- HTML coverage reports
- Coverage thresholds
- Multiple report formats

**When to Use:**

- Measuring test coverage
- Enforcing minimum coverage requirements
- Identifying untested code

---

### Coverage

**PyPI:** `coverage` | **Status:** Active | **Python:** 3.11+

Code coverage measurement and reporting tool.

**Key Features:**

- Statement and branch coverage
- HTML and XML reports
- Coverage API for custom reporting
- Configuration file support

**When to Use:**

- Understanding code coverage
- CI/CD coverage validation
- Code quality metrics

---

### mypy

**PyPI:** `mypy` | **Status:** Active | **Python:** 3.11+

Static type checker for Python. Verifies type hints without running code.

**Key Features:**

- Type hint verification
- Plugin system
- Incremental checking
- Multiple strictness levels
- Good error messages

**When to Use:**

- Type-checking Python code
- Catching type errors before runtime
- Enforcing type safety in projects
- Large codebase maintenance

---

### Ruff

**PyPI:** `ruff` | **Status:** Active | **Python:** 3.11+

Fast Python linter written in Rust. Combines flake8, isort, and other tools.

**Key Features:**

- Extreme speed (50-100x faster than flake8)
- Multiple rule sets
- Automatic fixing
- Isort-compatible import sorting
- Minimal configuration

**When to Use:**

- Linting Python code
- Replacing flake8, pylint, or isort
- CI/CD pipelines
- Code quality gates

---

### Black

**PyPI:** `black` | **Status:** Active | **Python:** 3.11+

Uncompromising code formatter. Enforces consistent style without configuration.

**Key Features:**

- Deterministic formatting
- Minimal configuration (intentional)
- AST-based (preserves semantics)
- Fast formatting
- Stable formatting output

**When to Use:**

- Enforcing code style
- Automatic code formatting
- Team collaboration (standardized style)
- CI/CD integration

---

### Hypothesis

**PyPI:** `hypothesis` | **Status:** Active | **Python:** 3.11+

Property-based testing framework. Generates test cases automatically.

**Key Features:**

- Property-based testing
- Automatic example generation
- Database of failing cases
- Integrated with pytest
- Profile systems for custom generation

**When to Use:**

- Property-based testing
- Testing invariants and properties
- Finding edge cases
- Fuzzing and robustness testing

---

## Async & Concurrency

### asyncio

**PyPI:** Built-in stdlib | **Status:** Maintained | **Python:** 3.11+

Standard library for asynchronous I/O and concurrent programming.

**Key Features:**

- Coroutines and tasks
- Event loop
- Futures for deferred results
- Synchronization primitives
- Subprocess support

**When to Use:**

- Any asynchronous Python code
- Built-in, no installation needed
- Building async applications
- Concurrent I/O operations

---

### Trio

**PyPI:** `trio` | **Status:** Active | **Python:** 3.11+

Friendly async library with better structured concurrency patterns.

**Key Features:**

- Structured concurrency (async with blocks)
- Better cancellation semantics
- Excellent debugging support
- Built-in testing utilities
- Simpler mental model than asyncio

**When to Use:**

- Complex async programs
- Structured concurrency patterns
- Better error handling in concurrent code
- Async testing

---

### uvloop

**PyPI:** `uvloop` | **Status:** Active | **Python:** 3.11+

Drop-in replacement for asyncio event loop, written in Cython for performance.

**Key Features:**

- 2-4x faster than default asyncio
- Drop-in replacement (single import)
- Works with all asyncio code
- libuv-based implementation
- Minimal overhead

**When to Use:**

- Performance-critical async applications
- Deploying async applications
- Speeding up existing asyncio code

**See Also:** `modern-modules/uvloop.md`

---

### APScheduler

**PyPI:** `apscheduler` | **Status:** Active | **Python:** 3.11+

Advanced Python Scheduler for task scheduling and automation.

**Key Features:**

- Cron-like scheduling
- Fixed interval scheduling
- One-off job scheduling
- Persistent job storage
- Multiple scheduler backends

**When to Use:**

- Scheduling recurring tasks
- Background job execution
- Cron-like task automation
- Building task queues

---

## Type Checking & Validation

### Pydantic

**PyPI:** `pydantic` | **Status:** Active | **Python:** 3.11+

See [Web Frameworks & APIs](#web-frameworks--apis) section above.

---

### attrs

**PyPI:** `attrs` | **Status:** Active | **Python:** 3.11+

Class definition library with minimal boilerplate, validators, and converters.

**Key Features:**

- Automatic dunder methods (`__init__`, `__repr__`, `__eq__`)
- Built-in validators and converters
- Slot-based classes for performance
- Frozen (immutable) classes
- Field transformers for extensibility

**When to Use:**

- Defining data classes with validation
- Creating immutable data structures
- Building domain models
- Performance-critical class definitions

**See Also:** `modern-modules/attrs.md`

---

### dataclasses

**PyPI:** Built-in stdlib | **Status:** Maintained | **Python:** 3.11+

Standard library for data classes with automatic dunder methods.

**Key Features:**

- Decorator-based class definition
- Automatic special methods
- Field configuration
- Slots support (Python 3.10+)
- Frozen classes

**When to Use:**

- Simple data container classes
- Zero external dependencies
- Built-in Python solution
- Python 3.10+ projects

---

### marshmallow

**PyPI:** `marshmallow` | **Status:** Active | **Python:** 3.11+

Object serialization/deserialization and data validation library.

**Key Features:**

- Field-based schema definition
- Serialization and deserialization
- Data validation
- Nested object support
- Extensive customization

**When to Use:**

- Data serialization and validation
- API request/response handling
- Legacy codebases
- Complex object mapping

---

## Configuration Management

### python-dotenv

**PyPI:** `python-dotenv` | **Status:** Active | **Python:** 3.11+

Load environment variables from .env files.

**Key Features:**

- Simple .env file parsing
- Environment variable injection
- Override control
- Interpolation support
- Path helpers

**When to Use:**

- Development environment setup
- Managing secrets and configuration
- Separating config from code
- Local development workflows

**See Also:** `modern-modules/python-dotenv.md`

---

### python-decouple

**PyPI:** `python-decouple` | **Status:** Active | **Python:** 3.11+

Simple library to separate configuration from code.

**Key Features:**

- Environment variable parsing
- Type casting (int, bool, list)
- Default value support
- Search order: env file, system env, defaults
- Minimal configuration

**When to Use:**

- Configuration management
- 12-factor app principles
- Simple environment variable handling

---

### dynaconf

**PyPI:** `dynaconf` | **Status:** Active | **Python:** 3.11+

Configuration management system supporting multiple formats and environments.

**Key Features:**

- YAML, TOML, JSON configuration
- Environment variable override
- Settings object with dot notation
- Multiple environments
- Validation support

**When to Use:**

- Complex configuration systems
- Multi-environment projects
- Configuration file management
- Settings management across environments

---

## Logging & Monitoring

### structlog

**PyPI:** `structlog` | **Status:** Active | **Python:** 3.11+

Structured logging library for adding context to log entries.

**Key Features:**

- Structured (JSON) logging
- Context preservation
- Processor pipelines
- Multiple output formats
- Integration with standard logging

**When to Use:**

- Building production systems
- Machine-readable log analysis
- Context propagation across function calls
- Structured logging infrastructure

---

### loguru

**PyPI:** `loguru` | **Status:** Active | **Python:** 3.11+

Simpler logging library with modern features and convenient API.

**Key Features:**

- Single logger instance
- Automatic file rotation
- Formatting with braces syntax
- Color output by default
- Exception formatting

**When to Use:**

- Simple logging setup
- Single-file modules
- Automatic formatting and rotation
- Convenient logging API

---

### OpenTelemetry

**PyPI:** `opentelemetry-api` | **Status:** Active | **Python:** 3.11+

Open standard for observability (metrics, traces, logs).

**Key Features:**

- Distributed tracing
- Metrics collection
- Log correlation
- Multiple exporter support
- Vendor-agnostic

**When to Use:**

- Distributed systems tracing
- Observability infrastructure
- Multi-service applications
- Monitoring and debugging

---

## Database & ORM

### SQLAlchemy

**PyPI:** `sqlalchemy` | **Status:** Active | **Python:** 3.11+

Most mature and feature-rich Python ORM and SQL toolkit.

**Key Features:**

- ORM for object-relational mapping
- Core expression language for queries
- Multiple database support
- Async support (SQLAlchemy 2.0+)
- Extensive customization

**When to Use:**

- Complex database applications
- Need ORM with full features
- Multiple database backend support
- Well-established projects

---

### Tortoise ORM

**PyPI:** `tortoise-orm` | **Status:** Active | **Python:** 3.11+

Async-first ORM inspired by Django ORM.

**Key Features:**

- Async/await native
- Django ORM-like API
- Multiple database support
- Migrations
- Validation

**When to Use:**

- Async applications
- FastAPI projects
- Django ORM-like experience with async
- Modern async web applications

---

### Peewee

**PyPI:** `peewee` | **Status:** Active | **Python:** 3.11+

Simple and small ORM for lightweight database interactions.

**Key Features:**

- Lightweight and simple API
- SQLite, PostgreSQL, MySQL support
- Query builder
- Migrations
- Expression-based querying

**When to Use:**

- Simple database applications
- Lightweight projects
- SQLite applications
- Learning ORM concepts

---

### asyncpg

**PyPI:** `asyncpg` | **Status:** Active | **Python:** 3.11+

Fast PostgreSQL database driver for asyncio.

**Key Features:**

- High performance (fastest Python PostgreSQL driver)
- Async/await support
- Native JSON support
- Connection pooling
- Streaming support

**When to Use:**

- PostgreSQL with async code
- High-performance database access
- FastAPI/Starlette applications
- Large-scale async applications

---

## Data Structures & Utilities

### attrs

**PyPI:** `attrs` | **Status:** Active | **Python:** 3.11+

See [Type Checking & Validation](#type-checking--validation) section above.

---

### bidict

**PyPI:** `bidict` | **Status:** Active | **Python:** 3.11+

Bidirectional dictionary supporting fast forward and reverse lookups.

**Key Features:**

- Bidirectional mapping
- Inverse access
- One-to-one mapping enforcement
- Immutable variants

**When to Use:**

- Bidirectional mappings
- ID-to-name relationships
- Reverse lookups required
- Enum-like behavior

**See Also:** `modern-modules/bidict.md`

---

### boltons

**PyPI:** `boltons` | **Status:** Active | **Python:** 3.11+

Set of utility functions for common programming tasks.

**Key Features:**

- Iteration utilities
- Dictionary utilities
- List utilities
- Table-like data structures
- Caching decorators

**When to Use:**

- Common utility operations
- Functional programming tools
- Extending standard library
- Utility collections

**See Also:** `modern-modules/boltons.md`

---

### python-diskcache

**PyPI:** `diskcache` | **Status:** Active | **Python:** 3.11+

Persistent disk-based dictionary-like cache for large datasets.

**Key Features:**

- Disk-based caching
- Dictionary interface
- LRU eviction
- Transactional semantics
- Compression support

**When to Use:**

- Caching large datasets
- Disk-persistent cache
- Building caches that survive restarts
- Replacing Redis for simple cases

**See Also:** `modern-modules/python-diskcache.md`

---

### Box

**PyPI:** `python-box` | **Status:** Active | **Python:** 3.11+

Dictionary with attribute-style access (dot notation).

**Key Features:**

- Attribute access to dictionary items
- Nested access support
- Configuration object pattern
- JSON export
- Validation integration

**When to Use:**

- Configuration objects
- Cleaner dictionary access syntax
- Nested data access
- Configuration management

**See Also:** `modern-modules/box.md`

---

### blinker

**PyPI:** `blinker` | **Status:** Active | **Python:** 3.11+

Signal (event) dispatching library for loose coupling.

**Key Features:**

- Signal/event dispatching
- Multiple listener support
- Weak references for cleanup
- Sender-based filtering
- Minimal dependencies

**When to Use:**

- Event-driven architecture
- Plugin systems
- Loose coupling between components
- Application signaling

**See Also:** `modern-modules/blinker.md`

---

## Serialization

### orjson

**PyPI:** `orjson` | **Status:** Active | **Python:** 3.11+

Fast JSON serialization library written in Rust.

**Key Features:**

- 10x faster than standard json
- Drop-in json replacement
- Native datetime serialization
- Supports numpy arrays
- Minimal dependencies

**When to Use:**

- High-performance JSON encoding
- Serializing numpy/pandas data
- Drop-in replacement for json
- Performance-critical serialization

---

### msgpack

**PyPI:** `msgpack` | **Status:** Active | **Python:** 3.11+

Binary serialization format for fast data interchange.

**Key Features:**

- Compact binary format
- Fast serialization/deserialization
- Support for various types
- Timestamp support
- Streaming support

**When to Use:**

- Binary message protocols
- High-performance serialization
- Network protocols
- RPC systems

---

### cattrs

**PyPI:** `cattrs` | **Status:** Active | **Python:** 3.11+

Custom class converters for attrs/dataclasses serialization.

**Key Features:**

- Serialization/deserialization
- Works with attrs and dataclasses
- Custom converters
- Nested structure support
- Structural polymorphism

**When to Use:**

- Converting attrs/dataclass to dictionaries
- Serializing complex structures
- attrs ecosystem serialization

---

## Templates & Code Generation

### Copier

**PyPI:** `copier` | **Status:** Active | **Python:** 3.11+

Project templating and scaffolding tool.

**Key Features:**

- Template-based project generation
- Question prompts during generation
- Relative path handling
- Pre-commit hooks
- Multi-layer templates

**When to Use:**

- Project scaffolding
- Template-based project generation
- Reproducible project structures
- Creating new projects

**See Also:** `modern-modules/copier.md`

---

### Jinja2

**PyPI:** `jinja2` | **Status:** Active | **Python:** 3.11+

Powerful templating engine for dynamic text generation.

**Key Features:**

- Template syntax with variables and filters
- Control flow (if/for/while)
- Custom filters and globals
- Template inheritance
- Auto-escaping

**When to Use:**

- HTML/template generation
- Code generation
- Dynamic document creation
- Report generation

---

## Automation & Deployment

### GitPython

**PyPI:** `GitPython` | **Status:** Active | **Python:** 3.11+

Python library for interacting with Git repositories.

**Key Features:**

- Repository operations
- Commit/branch management
- Remote operations
- Blame and history
- Config management

**When to Use:**

- Git integration in Python
- Automation with Git
- Repository analysis
- Deployment scripts

**See Also:** `modern-modules/GitPython.md`

---

### Fabric

**PyPI:** `fabric` | **Status:** Active | **Python:** 3.11+

See [CLI Development](#cli-development) section above.

---

### Prefect

**PyPI:** `prefect` | **Status:** Active | **Python:** 3.11+

Workflow orchestration and task scheduling platform.

**Key Features:**

- Task-based workflow definition
- Built-in retry and error handling
- Flow visualization
- Caching and result persistence
- API for monitoring

**When to Use:**

- Complex workflow orchestration
- Data pipeline management
- Task scheduling and execution
- Production workflow management

**See Also:** `modern-modules/prefect.md`

---

## Testing & Automation Frameworks

### Robot Framework

**PyPI:** `robotframework` | **Status:** Active | **Python:** 3.11+

Automation and testing framework with keyword-driven syntax.

**Key Features:**

- Keyword-driven testing
- Built-in libraries
- Custom library support
- Tabular data syntax
- HTML reports

**When to Use:**

- Acceptance testing
- Robotic process automation
- Non-technical test authoring
- End-to-end testing

**See Also:** `modern-modules/robotframework.md`

---

### Shiv

**PyPI:** `shiv` | **Status:** Active | **Python:** 3.11+

Command line utility to create self-contained zip applications.

**Key Features:**

- Creates executable Python applications
- Bundles dependencies
- Standalone distribution
- ZIP-based Python packages
- Single file distribution

**When to Use:**

- Distributing Python applications
- Creating standalone executables
- Shipping without pip
- Simple application distribution

**See Also:** `modern-modules/shiv.md`

---

### arrow

**PyPI:** `arrow` | **Status:** Active | **Python:** 3.11+

Friendlier datetime and timezone handling library.

**Key Features:**

- Human-friendly datetime API
- Timezone support
- Parsing and formatting
- Timezone conversion
- Relative time operations

**When to Use:**

- Datetime handling
- Timezone management
- Human-readable time formatting
- Datetime parsing

**See Also:** `modern-modules/arrow.md`

---

## Guide Structure

Each module typically includes:

1. **Overview** - What the module does and why it's useful
2. **Official Information** - Links, version, maintenance status
3. **Python Compatibility** - Supported Python versions
4. **Installation** - How to install (with uv recommended)
5. **Core Concepts** - Key ideas and patterns
6. **Usage Examples** - Practical code examples
7. **When to Use** - Decision guidance
8. **Alternatives** - Competing or complementary modules
9. **Integration Patterns** - How to use with other tools
10. **Common Gotchas** - Pitfalls and edge cases

## How to Navigate This Reference

### By Use Case

Start with the category that matches your need, then read the module descriptions.

### By Python Version

All modules listed are Python 3.11+ compatible. Check individual module references for exact version support.

### By Integration

Many modules work together (e.g., FastAPI + Pydantic, attrs + cattrs). Look for "See Also" and "Integration Patterns" sections.

### By Performance

For performance-critical code:

- **Serialization:** orjson, msgpack
- **Async I/O:** uvloop, httpx
- **Data processing:** Polars, DuckDB
- **Linting:** Ruff
- **Package management:** uv

## Installation Pattern

Install modules using uv (recommended) or pip:

```bash
# With uv
uv add module-name

# With pip (if uv not available)
pip install module-name
```

## Research Methodology

All modules in this reference are verified to be:

- Actively maintained (recent commits)
- Python 3.11+ compatible
- Production-ready
- Widely used in industry

Module information is gathered from:

- Official repositories and documentation
- PyPI package pages
- Community usage patterns
- Real-world project implementations

---

**Last Updated:** October 29, 2025 **Python Compatibility:** 3.11+ **Total Modules Covered:** 50+

For module-specific deep dives, see individual reference files in `modern-modules/`.
