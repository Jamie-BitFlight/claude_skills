---
title: "Dolt"
research_date: "2026-03-01"
source_url: "https://www.dolthub.com"
github_url: "https://github.com/dolthub/dolt"
version_at_research: "v1.83.0"
license: "Apache License 2.0"
last_verified: "2026-03-01"
version_at_verification: "v1.83.0"
next_review: "2026-06-01"
---

## Overview

Dolt is the world's first version-controlled SQL database, implementing Git semantics (branch, merge, diff, clone, push, pull) directly over relational data. It is fully MySQL-wire-protocol compatible, making it a drop-in replacement for MySQL applications while adding complete commit history, branching workflows, and auditable diffs at the row level. As of late 2025, Dolt achieves performance parity with MySQL on Sysbench benchmarks (0.99x multiplier).

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| No audit trail for database changes | Every SQL write can be a versioned commit with author, timestamp, and message — queryable via `dolt_log` system table |
| Cannot safely experiment with data without risking production state | Branches allow isolated experimentation; changes merge back only when validated |
| Multiple agents/processes writing shared state cause conflicts | Each agent works on its own branch; a coordinator merges branches with conflict resolution via stored procedures |
| Reproducing ML model runs requires snapshots of training data | Tag commits at training time; reproduce exact dataset with `AS OF` SQL syntax |
| Syncing changes between team members or environments requires manual coordination | `dolt push`/`dolt pull` remote operations sync commits like Git, with full conflict detection |
| Standard databases have no native diff: comparing two states requires full table scans | Prolly Tree storage computes diffs in O(d) time proportional to differences, not table size |
| ORM/driver incompatibility with `/`-delimited revision database names | `@` delimiter introduced in v1.83.0 as alias for `/` for Prisma, Hibernate, and similar tools |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 20,326 | 2026-03-01 |
| GitHub Forks | 643 | 2026-03-01 |
| Contributors | 125 | 2026-03-01 |
| Latest Release | v1.83.0 | 2026-03-01 |
| Open Issues | 519 | 2026-03-01 |
| Repository Age | Since 2019-07-24 | 2026-03-01 |
| Primary Language | Go | 2026-03-01 |

SOURCE: [GitHub API dolthub/dolt](https://api.github.com/repos/dolthub/dolt) (accessed 2026-03-01)

---

## Key Features

### MySQL Wire Protocol Compatibility

- Accepts connections from any MySQL client library (versions up to MySQL 8.4)
- Standard SQL: `SELECT`, `INSERT`, `UPDATE`, `DELETE`, joins, foreign keys, secondary indexes, triggers, check constraints
- Works with ORMs: Prisma, Hibernate, SQLAlchemy, ActiveRecord — `@` delimiter added in v1.83.0 for ORM URL compatibility
- `dolt sql-server` starts a server identical to `mysqld` from a client perspective
- Can be configured as a **Versioned MySQL Replica**: standard MySQL binlog replication where every write becomes a Dolt commit

SOURCE: [Dolt README](https://github.com/dolthub/dolt/blob/main/README.md) (accessed 2026-03-01)

### Branch and Merge Operations (SQL Stored Procedures)

All version control write operations are exposed as stored procedures callable from any SQL client:

- `CALL dolt_branch('branch-name')` — create a branch
- `CALL dolt_checkout('-b', 'branch-name')` — create and switch to branch
- `CALL dolt_add('table-name')` or `CALL dolt_add('-A')` — stage changes
- `CALL dolt_commit('-m', 'message')` — commit staged changes to HEAD
- `CALL dolt_merge('branch-name')` — merge named branch into current branch
- `CALL dolt_merge('branch-name', '--no-ff', '-m', 'message')` — merge with forced commit
- `CALL dolt_rebase('main')` — interactive rebase to rewrite commit history
- `CALL dolt_cherry_pick('commit-hash')` — apply specific commit to current branch
- `CALL dolt_reset('--hard', 'HEAD~1')` — undo commits
- `CALL dolt_revert('commit-hash')` — create a reverting commit
- `CALL dolt_stash()` / `CALL dolt_stash('pop')` — temporary save/restore
- `CALL dolt_push('origin', 'main')` / `CALL dolt_pull('origin')` — remote synchronization
- `CALL dolt_tag('v1.0', 'HEAD')` — tag commits
- `CALL dolt_gc()` — garbage collect unreferenced objects (requires admin)

SOURCE: [Dolt SQL Procedures Documentation](https://docs.dolthub.com/sql-reference/version-control/dolt-sql-procedures) (accessed 2026-03-01)

### Version Control System Tables (Read Operations)

System tables expose version history as queryable SQL data:

- `dolt_log` — commit history for current branch: `commit_hash`, `committer`, `email`, `date`, `message`, `commit_order`
- `dolt_commits` — all commits across the entire database regardless of branch
- `dolt_branches` — all branches with HEAD commit hashes and metadata
- `dolt_status` — current working set state (staged/unstaged changes)
- `dolt_diff_$TABLENAME` — per-table row-level diffs showing `from_X`/`to_X` columns for each column X
- `dolt_commit_diff_$TABLENAME` — diff between any two commits: requires `from_commit` and `to_commit` parameters; accepts `WORKING` as `to_commit`
- `dolt_history_$TABLENAME` — every historical version of every row in a table
- `DOLT_DIFF()` table function — ad-hoc diff calculation between any two refs without per-table tables

SQL `AS OF` syntax for time-travel queries:

```sql
SELECT * FROM mytable AS OF 'main~3';
SELECT * FROM mytable AS OF 'abc123def456';
SELECT * FROM mytable AS OF CONVERT('2025-01-01', CHAR);
```

SOURCE: [Dolt System Tables Documentation](https://docs.dolthub.com/sql-reference/version-control/dolt-system-tables) (accessed 2026-03-01)

### CLI Interface

The Dolt CLI mirrors Git's command surface precisely:

```text
dolt init          # Initialize empty Dolt repository
dolt sql            # Interactive SQL shell
dolt sql-server    # Start MySQL-compatible server
dolt add <table>   # Stage table changes
dolt commit -m "message"
dolt status
dolt diff [table]
dolt log
dolt branch <name>
dolt checkout <branch>
dolt merge <branch>
dolt clone <remote>
dolt fetch / pull / push
dolt blame <table>
dolt filter-branch
dolt table import / export  # CSV, JSON, JSONL (v1.83.0+), Parquet
```

SOURCE: [Dolt README](https://github.com/dolthub/dolt/blob/main/README.md) (accessed 2026-03-01)

### Agentic Memory and Multi-Agent Coordination

DoltHub explicitly markets Dolt as "The Database for AI" because of its suitability for agentic memory:

- **Persistent cross-session memory**: Agents write structured task state, observations, and plans to Dolt tables and commit after each session; next session queries the latest HEAD
- **Parallel agent isolation**: Each agent gets its own branch, preventing write conflicts while sharing the same base state
- **Merge coordination**: A coordinator agent or human merges agent branches after review, with conflict detection at the row level
- **Audit trail**: Every agent action is a traceable commit with author identity and timestamp
- **Rollback**: If an agent makes bad writes, `CALL dolt_reset('--hard', 'HEAD~N')` reverts to clean state
- **Session continuity**: The Beads agentic memory project (backed by Dolt) demonstrated 12-hour continuous operation versus typical 1-hour sessions by persisting task context between sessions

SOURCE: [Agentic Memory | DoltHub Blog](https://www.dolthub.com/blog/2026-01-22-agentic-memory/) (accessed 2026-03-01)

### Performance

Performance history against MySQL Sysbench benchmarks:

- 2021: ~15x slower than MySQL
- Early 2024: ~2x slower (reads and writes)
- End of 2024: ~25% slower reads, ~13% faster writes
- Late 2025: **0.99x multiplier — statistical parity with MySQL**

Optimizations that achieved parity: passing tree nodes as pointers, making branch activity tracking opt-in (removing from hot paths), Go runtime tuning.

JSON performance: Dolt outperforms MySQL on large JSON documents (>64KB) because MySQL loads entire documents into memory while Dolt uses content-addressed chunking.

SOURCE: [Dolt is as Fast as MySQL on Sysbench | DoltHub Blog](https://www.dolthub.com/blog/2025-12-04-dolt-is-as-fast-as-mysql/) (accessed 2026-03-01)

---

## Technical Architecture

### Prolly Trees (Probabilistic B-Trees)

Dolt's core innovation is the **Prolly Tree** — a variant of B-tree that uses content-addressed storage (similar to Git's object store):

1. **Content-addressed chunks**: All data is stored in variable-size chunks, each addressed by the SHA hash of its content. Identical content across versions is stored once and referenced by multiple commits (structural sharing).
2. **History independence**: Regardless of insert order, the Prolly Tree for the same data set produces the same root hash. This property enables merge and diff without tracking change history.
3. **Fast diffs**: Two Prolly Trees can be compared by recursively comparing chunk hashes from the root. If a subtree's root hash matches, the entire subtree is identical. Diff time is O(d) where d = number of changed rows, not O(n) where n = total rows.
4. **Merge via three-way diff**: Merging two branches computes `diff(ancestor, branch-A)` and `diff(ancestor, branch-B)`, then applies non-conflicting changes; row-level conflicts are surfaced in `dolt_conflicts_$TABLENAME` for manual resolution.

What Dolt stores in Prolly Trees:

- Table data: primary key → column values
- Secondary indexes: index values → primary key references
- Schemas: stored as trees for efficient root hash calculation
- Keyless tables: all columns treated as composite primary key with duplicate counts

### Commit Graph

Like Git, Dolt maintains a DAG of commits. Each commit stores:

- Root hash of the entire database state (one hash covers all tables)
- Parent commit hashes (one for regular commits, two for merges)
- Author, committer, timestamp, message

Branch names are pointers to commit hashes (like Git refs). The `main` branch is the default.

### Server Architecture

`dolt sql-server` implements the MySQL wire protocol (MySQL 5.7/8.0 compatible) using the **go-mysql-server** library (also maintained by DoltHub). Multiple concurrent sessions are supported. Each session can be on a different branch by connecting to `dbname/branchname` or `dbname@branchname` (v1.83.0+).

```text
MySQL Client
     |
     | MySQL Wire Protocol (port 3306 default)
     v
dolt sql-server
     |
     +-- go-mysql-server (query parsing, planning, optimization)
     |
     +-- Dolt storage engine
          |
          +-- Prolly Tree index/data storage
          |
          +-- Content-addressed block store (local filesystem)
          |
          +-- Remote: DoltHub / DoltLab / any HTTP remote
```

SOURCE: [Prolly Trees Architecture](https://docs.dolthub.com/architecture/storage-engine/prolly-tree) (accessed 2026-03-01)

---

## Installation & Usage

### Installation

```bash
# Linux/macOS one-line install
sudo bash -c 'curl -L https://github.com/dolthub/dolt/releases/latest/download/install.sh | bash'

# macOS Homebrew
brew install dolt

# Arch Linux
pacman -S dolt

# Windows Chocolatey
choco install dolt

# Docker (server mode)
docker run -p 3306:3306 dolthub/dolt-sql-server

# From source (requires Go + C compiler)
go install github.com/dolthub/dolt/go/cmd/dolt@latest
```

### Initialize and Basic Workflow

```bash
# Create a new Dolt repository
mkdir mydb && cd mydb
dolt init

# Start SQL server
dolt sql-server &

# Connect with any MySQL client
mysql --host 127.0.0.1 --port 3306 -u root
```

```sql
-- Create a table and insert data
CREATE DATABASE myapp;
USE myapp;
CREATE TABLE tasks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255),
    status VARCHAR(50),
    agent_id VARCHAR(100)
);
INSERT INTO tasks (title, status, agent_id) VALUES ('Research feature X', 'pending', 'agent-1');

-- Stage and commit (like git add && git commit)
CALL dolt_add('tasks');
CALL dolt_commit('-m', 'Add initial tasks table');

-- View commit history
SELECT commit_hash, committer, date, message FROM dolt_log;
```

### Branching Workflow for Parallel Agents

```sql
-- Agent 1: create its own branch and work there
CALL dolt_checkout('-b', 'agent-1-session');
INSERT INTO tasks (title, status, agent_id) VALUES ('Implement auth', 'in_progress', 'agent-1');
CALL dolt_add('-A');
CALL dolt_commit('-m', 'agent-1: start auth implementation');

-- Agent 2: working on main branch simultaneously (separate connection)
-- USE myapp/main; (or connect to 'myapp@main' for ORM compatibility)
INSERT INTO tasks (title, status, agent_id) VALUES ('Write tests', 'pending', 'agent-2');
CALL dolt_add('-A');
CALL dolt_commit('-m', 'agent-2: add test task');

-- Coordinator: merge agent-1's work back to main
-- USE myapp/main;
CALL dolt_merge('agent-1-session', '--no-ff', '-m', 'Merge agent-1 session results');
```

### Time-Travel and Audit Queries

```sql
-- View all changes to 'tasks' table across all commits
SELECT * FROM dolt_diff_tasks ORDER BY to_commit_date DESC;

-- See what changed between two commits
SELECT diff_type, from_title, to_title, from_status, to_status
FROM dolt_commit_diff_tasks
WHERE from_commit = 'abc123' AND to_commit = 'def456';

-- Query the database as it existed 5 commits ago
SELECT * FROM tasks AS OF 'HEAD~5';

-- Query as of a specific date
SELECT * FROM tasks AS OF '2025-12-01 00:00:00';
```

### Python Integration (Modern Approach)

The recommended Python approach is to use any MySQL client library against a running `dolt sql-server`:

```python
import mysql.connector

# Connect to Dolt like any MySQL database
conn = mysql.connector.connect(host="127.0.0.1", port=3306, user="root", password="", database="myapp")
cursor = conn.cursor()

# Version control operations via stored procedures
cursor.execute("CALL dolt_checkout('-b', 'agent-session-001')")
cursor.execute("INSERT INTO tasks (title, status) VALUES (%s, %s)", ("New task", "pending"))
cursor.execute("CALL dolt_add('-A')")
cursor.execute("CALL dolt_commit('-m', 'Agent session 001 results')")
conn.commit()

# Query history
cursor.execute("SELECT commit_hash, message, date FROM dolt_log LIMIT 10")
for row in cursor.fetchall():
    print(row)
```

### Legacy Python SDK (doltpy — low-maintenance)

```bash
pip install doltpy
```

```python
from doltpy.cli import Dolt

# CLI-wrapper approach (wraps dolt binary)
db = Dolt.init("/path/to/mydb")
db.sql("INSERT INTO tasks VALUES (...)")
db.add("tasks")
db.commit(message="Add task via Python")
```

Note: doltpy is in low-maintenance mode as of 2024. New projects should use `mysql.connector`, `pymysql`, or `sqlalchemy` with `dolt sql-server`.

SOURCE: [doltpy PyPI](https://pypi.org/project/doltpy/) (accessed 2026-03-01), [doltpy GitHub](https://github.com/dolthub/doltpy) (accessed 2026-03-01)

### Go API

Dolt's native language is Go. Embed as a library:

```go
import (
    "github.com/dolthub/dolt/go/libraries/doltcore/env"
    "github.com/dolthub/dolt/go/libraries/doltcore/doltdb"
)

// Open existing Dolt repository
fs := filesys.LocalFS
dEnv := env.Load(ctx, env.GetCurrentUserHomeDir, fs, doltdb.LocalDirDoltDB, "")
doltDB := dEnv.DoltDB

// Create branch
err := doltDB.NewBranchAtCommit(ctx, ref.NewBranchRef("my-branch"), headCommit)
```

For most Go use cases, the recommended approach is spawning `dolt sql-server` and connecting via `go-sql-driver/mysql`.

---

## Relevance to Claude Code Development

### Applications

- **Persistent agent memory across sessions**: Claude Code agents can write structured observations, task state, and findings to Dolt tables. Each session commit creates a permanent, queryable record. The Beads case study showed 10x session duration improvement with versioned memory.
- **Multi-agent coordination without file conflicts**: Rather than multiple agents editing shared files (causing Git merge conflicts at the file level), agents write to Dolt branches and merge at the row level — finer-grained conflict detection.
- **Audit trail for automated changes**: Every `INSERT`/`UPDATE` made by an agent is traceable to a specific commit with timestamp. Debugging agent behavior becomes querying `dolt_diff_$table`.
- **Rollback of bad agent actions**: If an autonomous agent corrupts shared state, `CALL dolt_reset('--hard', 'COMMIT_BEFORE_DAMAGE')` restores cleanly without touching other tables.
- **Versioned configuration and prompt databases**: Store system prompts, tool configurations, and knowledge bases in Dolt tables. Promote configuration changes through branches (dev → staging → prod).

### Patterns Worth Adopting

- **Branch-per-agent pattern**: Each Claude Code subagent session gets its own branch. Branches are cheap (just a pointer). The coordinator merges approved branches back to main after verification. This maps directly to the swarm-task-planner workflow.
- **Commit-per-checkpoint**: Agents call `CALL dolt_commit()` after each significant action (completing a task step, finishing a research session). This gives fine-grained recovery points.
- **`AS OF` for reproducible queries**: Test evaluation harnesses can lock dataset versions with `SELECT * FROM eval_cases AS OF 'v2.1'` to guarantee reproducible benchmark runs.
- **`dolt_log` as agent activity feed**: `SELECT * FROM dolt_log WHERE committer = 'agent-007' ORDER BY date DESC` gives a complete activity history for any agent.
- **Conflict tables for coordination signals**: When two agents write conflicting rows, `dolt_conflicts_$table` surfaces them — this is a structured coordination signal rather than an unstructured file conflict.

### Integration Opportunities

- **Replace file-based task state in SAM workflow**: The current `plan/tasks-*.md` files could be stored in Dolt tables, enabling agents to query task status via SQL rather than parsing markdown. `CALL dolt_commit()` after each status update provides automatic versioning.
- **Shared knowledge base**: Research entries (currently in `./research/`) could live in Dolt tables with structured schema (category, resource_name, stars, reviewed_at), queryable and diffable across research sessions.
- **Multi-agent experiment coordination**: When running parallel evaluation agents, each agent branch captures its subset of results; a coordinator merges and resolves any duplicate rows using Dolt's conflict resolution.
- **MySQL-drop-in for existing tool integrations**: Any tool in the plugin ecosystem that supports MySQL (LangChain memory stores, LlamaIndex vector + relational stores, etc.) can point at Dolt and gain version control transparently.

---

## References

- [GitHub Repository: dolthub/dolt](https://github.com/dolthub/dolt) (accessed 2026-03-01)
- [What is Dolt? — Official Documentation](https://docs.dolthub.com/introduction/what-is-dolt) (accessed 2026-03-01)
- [Dolt SQL Stored Procedures](https://docs.dolthub.com/sql-reference/version-control/dolt-sql-procedures) (accessed 2026-03-01)
- [Dolt System Tables Reference](https://docs.dolthub.com/sql-reference/version-control/dolt-system-tables) (accessed 2026-03-01)
- [Prolly Tree Architecture](https://docs.dolthub.com/architecture/storage-engine/prolly-tree) (accessed 2026-03-01)
- [Agentic Memory | DoltHub Blog](https://www.dolthub.com/blog/2026-01-22-agentic-memory/) (accessed 2026-03-01)
- [How I Use Multiple Agents in Parallel | DoltHub Blog](https://www.dolthub.com/blog/2025-08-28-how-i-use-multiple-agents-in-parallel/) (accessed 2026-03-01)
- [Dolt is as Fast as MySQL on Sysbench | DoltHub Blog](https://www.dolthub.com/blog/2025-12-04-dolt-is-as-fast-as-mysql/) (accessed 2026-03-01)
- [How Dolt Got as Fast as MySQL | DoltHub Blog](https://www.dolthub.com/blog/2025-12-12-how-dolt-got-as-fast-as-mysql/) (accessed 2026-03-01)
- [10% Slower Than MySQL — 2024 Performance Summary | DoltHub Blog](https://www.dolthub.com/blog/2024-12-23-2024-perf-summary/) (accessed 2026-03-01)
- [doltpy Python Library — GitHub](https://github.com/dolthub/doltpy) (accessed 2026-03-01)
- [doltpy — PyPI](https://pypi.org/project/doltpy/) (accessed 2026-03-01)
- [GitHub API: dolthub/dolt repository metadata](https://api.github.com/repos/dolthub/dolt) (accessed 2026-03-01)
- [GitHub Release v1.83.0](https://github.com/dolthub/dolt/releases/tag/v1.83.0) (accessed 2026-03-01)

---
