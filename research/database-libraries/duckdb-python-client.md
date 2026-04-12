---
name: duckdb-python-client
category: database-libraries
resource: DuckDB Python Client
url: https://duckdb.org/docs/stable/clients/python/overview.html
accessed: 2026-04-12
---

# DuckDB Python Client

## Overview

The DuckDB Python client is the official Python binding for DuckDB, an in-process, columnar, OLAP (Online Analytical Processing) database engine. The Python client provides idiomatic access to DuckDB's SQL query engine and relational data processing capabilities from Python applications.

**Key characteristics:**
- Zero external dependencies; runs in-process in the host application
- Supports both ephemeral in-memory databases and persistent database files
- Provides two primary APIs: the high-level Relational API and the low-level DB-API 2.0 (PEP 249) interface
- Fully featured columnar SQL engine optimized for analytical queries
- Portable across Linux, macOS, Windows, and other platforms

**Repository**: <https://github.com/duckdb/duckdb-python>
**Package name**: `duckdb` (PyPI)
**Current stable version**: 1.5.1 (as of 2026-04-12)

---

## Problem Addressed

The DuckDB Python client solves several pain points in analytical data processing:

1. **Simplicity**: Unlike traditional RDBMS clients that require separate server infrastructure, DuckDB runs in-process with zero external dependencies, eliminating deployment complexity.

2. **Performance**: Provides blazing-fast analytical query execution through a columnar storage format and vectorized query engine optimized for large dataset scans rather than single-row lookups.

3. **Data format flexibility**: Can read and write CSV, Parquet, JSON, and other formats directly from local filesystems and remote endpoints (S3, HTTP URLs), without intermediate data loading.

4. **Language integration**: Bridges Python's data ecosystem (pandas, Polars, PyArrow, PySpark) with SQL's expressiveness—users can mix DataFrames and SQL seamlessly.

---

## Key Statistics

- **Python support**: Requires Python 3.9 or newer (tested on 3.10, 3.11, 3.12, 3.13, 3.14)
- **Package size**: Distributed as pre-built wheels for major platforms (macOS x86_64/arm64, Linux x86_64/aarch64, Windows AMD64/ARM64); source sdist also available
- **Installation methods**:
  - Standard: `pip install duckdb`
  - With optional dependencies: `pip install 'duckdb[all]'`
  - Via conda: `conda install python-duckdb -c conda-forge`
- **License**: MIT (permissive open-source)
- **Maintainer**: DuckDB Foundation

---

## Key Features

### 1. Connection and Database Management

The Python client exposes two primary entry points:

**Global default connection** (via `duckdb.sql()`):
```python
import duckdb
duckdb.sql("SELECT 42").show()
```
Executes queries on an in-memory database stored globally within the Python module. Suitable for ad-hoc queries and prototyping.

**Persistent database connections** (via `duckdb.connect()`):
```python
conn = duckdb.connect('my_database.duckdb')
result = conn.execute("SELECT * FROM my_table").fetchall()
```
Creates a connection to a persistent database file. Data written through the connection is immediately persisted and can be reloaded by reconnecting to the same file from any DuckDB client.

### 2. Relational API

Beyond SQL, DuckDB provides a Relational (object-oriented) API for programmatic query construction and DataFrame interoperability:

- **Relations**: DuckDB's primary abstraction for working with data (represented by `DuckDBPyRelation` objects in Python)
- **Chainable operations**: Filter, project, aggregate, join, and window function operations can be chained programmatically
- **Zero-copy integration**: Direct bindings to PyArrow, Pandas, and Polars DataFrames without intermediate copies

### 3. Data Format Support

The client natively reads and writes:
- **Structured formats**: CSV, Parquet, JSON, ORC, Iceberg
- **Remote sources**: S3 buckets, HTTP URLs, GCS, Azure Blob Storage
- **Python objects**: Pandas DataFrames, Polars DataFrames, PyArrow Tables, record dictionaries
- **Direct file queries**: `SELECT * FROM 'file.parquet'` (no prior load step required)

### 4. Python User-Defined Functions (UDFs)

The `@duckdb.create_function` decorator allows users to define custom functions in Python that execute within the SQL engine:
```python
@duckdb.create_function
def my_custom_function(x):
    return x * 2

conn.execute("SELECT my_custom_function(10)").fetchall()
```

### 5. Exception Handling

The Python client exports a comprehensive exception hierarchy for fine-grained error handling:
- `DuckDBError` (base class)
- Query execution errors: `ParserException`, `BinderException`, `CatalogException`, `InvalidInputException`
- Data errors: `DataError`, `IntegrityError`, `ConversionException`, `TypeMismatchException`
- I/O errors: `IOException`, `HTTPException`
- System errors: `InternalException`, `OutOfMemoryException`, `InterruptException`

### 6. Extensions

The client supports DuckDB's extension system, allowing third-party features to be loaded:
- JSON processing, ICU text operations, Parquet/Iceberg support
- Built-in extensions include `json`, `parquet`, `icu`, `jemalloc`
- Community extensions available via `INSTALL` and `LOAD` SQL commands

### 7. Query Introspection

- `EXPLAIN` statements with multiple output formats (text, JSON)
- Query profiling via `enable_profiling()` and `disable_profiling()`
- Statement preparation and parameterized queries via `execute(statement, parameters)`

---

## Technical Architecture

### Core Components

**1. Python Binding Layer (pybind11)**
The Python client is implemented as a C++ extension module (`_duckdb`) built with pybind11. This binding layer exposes:
- `DuckDBPyConnection`: Main interface for database connections; wraps the underlying C++ `Connection` object
- `DuckDBPyRelation`: Represents a relational query result or table; wraps the C++ `Relation` class
- Exception classes mapped from C++ exceptions to Python exception types

**2. Connection Object (`DuckDBPyConnection`)**
Represents an active connection to a DuckDB database instance. Primary responsibilities:
- Query execution via `execute()`, `executemany()` methods
- Transaction management: `begin()`, `commit()`, `rollback()`
- Cursor creation: `cursor()` method for DB-API 2.0 compliance
- Relation creation: `from_df()`, `from_arrow()`, `from_parquet()`, etc.
- Schema inspection: `execute("SELECT * FROM information_schema.tables")`

**3. Relation Object (`DuckDBPyRelation`)**
Represents a relation (table, query result, or DataFrame). Supports:
- SQL query execution on relations: `rel.filter("column > 5")`
- Format conversion: `rel.to_df()`, `rel.to_arrow()`, `rel.to_parquet()`
- I/O operations: `rel.write_parquet()`, `rel.write_csv()`
- Materialization: `rel.collect()` to fetch all results into memory

**4. DB-API 2.0 Compliance (`cursor` API)**
The `connection.cursor()` method returns a cursor object that implements PEP 249 (DB-API 2.0), allowing compatibility with existing Python database tooling:
```python
cursor = conn.cursor()
cursor.execute("SELECT * FROM table")
rows = cursor.fetchall()
```

### Data Flow

1. **Query input**: User passes SQL string or constructs a Relation programmatically
2. **Parsing**: SQL parser (C++ component) tokenizes and builds an AST
3. **Binding**: Type binder resolves column references and function calls
4. **Planning**: Query optimizer generates an execution plan
5. **Execution**: Vectorized query engine processes data in columnar batches
6. **Result collection**: Results are materialized into Python objects (tuples, DataFrames, PyArrow Tables) or returned as an iterator
7. **Format export**: Results can be exported to CSV, Parquet, JSON, or other formats

### Extension Mechanism

Extensions are loaded via SQL:
```sql
INSTALL json;
LOAD json;
```

Each extension is a dynamically-loaded C++ plugin that registers custom types, functions, and table functions with the engine. The Python client automatically discovers and exposes extension APIs.

---

## Installation & Usage

### Installation

```bash
pip install duckdb
```

For optional dependencies (e.g., Polars integration, community extensions):
```bash
pip install 'duckdb[all]'
```

### Basic Usage

**1. Simple query execution:**
```python
import duckdb

# Using default in-memory connection
duckdb.sql("SELECT 42 AS answer").show()
# Output: answer
#         42
```

**2. Persistent database:**
```python
conn = duckdb.connect('my_database.duckdb')
conn.execute("CREATE TABLE numbers (id INTEGER, value DOUBLE)")
conn.execute("INSERT INTO numbers VALUES (1, 3.14), (2, 2.71)")
conn.execute("SELECT * FROM numbers WHERE value > 3").show()
```

**3. Working with DataFrames:**
```python
import pandas as pd

df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
result = duckdb.from_df(df).filter("x > 1").to_df()
print(result)
```

**4. Reading remote Parquet files:**
```python
result = duckdb.sql(
    "SELECT COUNT(*) FROM 's3://my-bucket/data.parquet'"
)
```

**5. User-defined function:**
```python
@duckdb.create_function
def double(x):
    return x * 2

duckdb.sql("SELECT double(5)").show()
```

**6. Exception handling:**
```python
from duckdb import ParserException, CatalogException

try:
    conn.execute("SELECT * FROM nonexistent_table")
except CatalogException as e:
    print(f"Table not found: {e}")
except ParserException as e:
    print(f"SQL syntax error: {e}")
```

### Configuration Options

Common connection parameters:
- `read_only=True`: Open database in read-only mode
- `memory_limit='1GB'`: Set memory budget for queries
- `threads=4`: Number of parallel query execution threads
- `timeout=30000`: Query timeout in milliseconds

```python
conn = duckdb.connect(
    'my_db.duckdb',
    read_only=False,
    config={'memory_limit': '2GB', 'threads': 8}
)
```

---

## Limitations and Caveats

### Known Limitations

1. **Free-threaded Python not supported**: The production duckdb-python client does not support free-threaded Python variants (`3.13t`, `3.14t`). A separate prototype exists targeting free-threading, Stable ABI, and multi-interpreter support.

2. **Single-writer model**: While multiple readers can access a database simultaneously, only one writer can hold an exclusive lock at a time. Concurrent write access requires external coordination (e.g., file-level locks, distributed locking service).

3. **In-memory aggregations**: Very large GROUP BY operations may spill to disk but can still exhaust available memory if the result set exceeds memory limits.

4. **Correlated subquery optimization**: Complex correlated subqueries may not be as optimized as modern query planners; rewriting as joins often yields better performance.

5. **Dynamic SQL limitations**: Parameterized queries are recommended over string interpolation for security and performance; dynamic column/table names require careful escaping via `duckdb.sql.identifier()`.

### Extensions and Boundaries

- Extensions must be explicitly installed and loaded; they are not automatically available
- Some extensions (e.g., DuckDB's JSON extension) are bundled in the wheel; others require `INSTALL` from the extension repository
- Community-contributed extensions may not have the same support SLA as core extensions

### Absence of Documented Limitations

No specific performance benchmarks (throughput, latency, memory overhead) are documented in official overview documentation reviewed. Performance characteristics are context-dependent (workload size, hardware, query complexity).

---

## Relevance to Claude Code Development

### 1. Data Analysis and Reporting

DuckDB's Python client enables Claude Code agents to process and analyze data locally without external database infrastructure. Agents can:
- Load CSV/Parquet files and run analytical SQL queries
- Generate reports by querying structured data
- Transform datasets via SQL rather than procedural Python code

### 2. AI Agent Data Grounding

For agents that reason about datasets:
- Query file-based data sources (S3, local files) directly within the agent prompt execution
- Join multiple data sources without loading into memory explicitly
- Use SQL's declarative expressiveness alongside Python's procedural logic

### 3. Temporary Data Staging

Claude Code workflows can use DuckDB's in-memory mode for:
- Staging and validating data before writing to persistent storage
- Testing data transformation logic without database setup
- Ephemeral aggregate computations (no persistent state needed)

### 4. Data Validation Automation

Agents can build validation pipelines:
```python
conn = duckdb.connect(':memory:')
conn.execute("CREATE TABLE raw_data AS SELECT * FROM 'input.csv'")
conn.execute("SELECT COUNT(*) FROM raw_data WHERE id IS NULL")  # null checks
```

### 5. Format Conversion Workflows

DuckDB can automate data format transformations:
- Load CSV → convert to Parquet (preserving schema and compression)
- Read Parquet → export as JSON with custom formatting
- Pipeline data through multiple formats in a single workflow

### 6. Integration with Python Data Ecosystem

Direct interoperability with:
- **Pandas**: `df = duckdb.from_df(pandas_df)` and `duckdb_rel.to_df()`
- **Polars**: Native Polars DataFrame integration
- **PyArrow**: Zero-copy table exchange via Arrow IPC
- **PySpark**: Experimental compatibility layer for Spark DataFrame interchange

### 7. Testing Data-Driven Agents

Agents that operate on data can:
- Use DuckDB's in-memory mode for test harness setup
- Parameterize tests with data from CSV/Parquet fixtures
- Validate output schemas using SQL schema inspection

---

## References

- [DuckDB Official Documentation](https://duckdb.org/docs/stable/clients/python/overview.html) — Overview documentation for Python client API (accessed 2026-04-12)
- [DuckDB Python API Reference](https://duckdb.org/docs/stable/clients/python/reference/index.html) — Detailed API reference (accessed 2026-04-12)
- [DuckDB GitHub Repository](https://github.com/duckdb/duckdb) — Core engine source
- [duckdb-python Repository](https://github.com/duckdb/duckdb-python) — Python bindings source; pybind11-based C++ extension
- [PyPI Package](https://pypi.org/project/duckdb/) — Python package distribution
- Real Python Guide: [Introducing DuckDB](https://realpython.com/python-duckdb/) — Practical tutorial covering connection management, SQL execution, DataFrame integration (accessed 2026-04-12)

---

## Freshness Tracking

**Last reviewed**: 2026-04-12
**Next review**: 2026-07-12 (90 days)

### Confidence by Section

| Section | Confidence | Notes |
|---------|-----------|-------|
| Overview | high | Official documentation, current as of stable release 1.5.1 |
| Problem Addressed | high | Documented in README and official docs |
| Key Statistics | high | PyPI package information, Python version support verified from README |
| Key Features | high | Extracted from duckdb/__init__.py, README, official API docs |
| Technical Architecture | medium | Derived from pybind11 binding patterns and duckdb/__init__.py component names; full architecture details require review of C++ source |
| Installation & Usage | high | Verified from official documentation and README examples |
| Limitations | high | Documented in CLAUDE.md and repository code comments |
| Relevance to Claude Code | medium | Inferred from DuckDB's capabilities; not explicitly stated in official documentation |

### Changes Since Last Review

Initial research entry created on 2026-04-12. No prior review history.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [MotherDuck](../data-infrastructure/motherduck.md) | data-infrastructure | serverless cloud platform extending DuckDB with hybrid local+cloud execution |
| [Polars Documentation](../data-infrastructure/polars-documentation.md) | data-infrastructure | alternative columnar DataFrame engine with lazy evaluation; shared integration with pandas and PyArrow |
| [Pandera](../data-infrastructure/pandera.md) | data-infrastructure | statistical data validation library with multi-backend support for DuckDB queries |
| [Dolt](../data-infrastructure/dolt.md) | data-infrastructure | version-controlled SQL database with Git semantics; alternative to DuckDB for applications requiring branching and merge tracking |
