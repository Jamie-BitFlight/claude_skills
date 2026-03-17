---
task: T1
title: Implement database migration framework
status: not-started
agent: python3-development:python-cli-architect
dependencies: []
priority: 2
complexity: high
skills:
  - python3-development
blocked-by: []
parallelize-with: []
accuracy-risk: medium
---

### Context

The application currently has no database migration framework. Schema changes
are applied manually via SQL scripts, which is error-prone and not reproducible.

### Objective

Create an Alembic-based migration framework with auto-generation support and
a CLI wrapper for common migration operations.

### Requirements

1. Initialize Alembic with async SQLAlchemy configuration.
2. Create initial migration from existing models.
3. Add CLI commands: `db upgrade`, `db downgrade`, `db revision`.

### Acceptance Criteria

- `db upgrade head` applies all pending migrations
- `db downgrade -1` rolls back the most recent migration
- Auto-generated migrations detect new columns and tables
