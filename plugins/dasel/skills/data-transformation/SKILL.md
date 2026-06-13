---
name: data-transformation
description: Use when modifying, converting, or transforming structured data with dasel v3 — in-place mutations, format conversion, batch operations, array manipulation, object construction, and merge patterns across JSON, YAML, TOML, XML, CSV, HCL, INI
---

# Data Transformation with Dasel v3

<when_to_use>

Activate this skill when:

- Modifying values in config files (YAML, TOML, JSON, XML, HCL, INI)
- Converting between data formats (JSON to YAML, TOML to JSON, etc.)
- Batch-updating array elements (prices, versions, flags)
- Appending, removing, or reshaping data structures
- Merging objects or constructing new structures from existing data

</when_to_use>

## Safety Rules

<constraints>

**NEVER redirect output to the same input file.** This truncates the file before dasel reads it, resulting in data loss:

```bash
# WRONG — destroys input
cat config.yaml | dasel -i yaml --root 'port = 9090' > config.yaml

# CORRECT — write to temp, then rename
cat config.yaml | dasel -i yaml --root 'port = 9090' > config_tmp.yaml && mv config_tmp.yaml config.yaml
```

**Always verify before overwriting.** Preview the transformation output first, then redirect:

```bash
# Preview
cat config.yaml | dasel -i yaml --root 'server.port = 9090'
# Apply
cat config.yaml | dasel -i yaml --root 'server.port = 9090' > config_tmp.yaml && mv config_tmp.yaml config.yaml
```

</constraints>

## Core Modification Syntax

In dasel v3, `put` and `delete` subcommands do not exist. All modifications use assignment expressions with `--root` to output the full document.

### Set a Value

```bash
# Output full document with one field changed
cat config.yaml | dasel -i yaml --root 'server.port = 9090'

# Numeric, boolean, and string assignments
echo '{"count": 1}' | dasel -i json --root 'count = 42'
echo '{"enabled": false}' | dasel -i json --root 'enabled = true'
echo '{"name": "old"}' | dasel -i json --root 'name = "new"'
```

### Set Nested Values

```bash
cat config.yaml | dasel -i yaml --root 'database.connection.host = "db.example.com"'
cat config.yaml | dasel -i yaml --root 'database.connection.port = 5432'
```

## In-Place Modification (Safe Pattern)

```bash
# Single field update
cat config.yaml | dasel -i yaml --root 'server.port = 9090' > config_tmp.yaml && mv config_tmp.yaml config.yaml

# Multiple fields — chain with semicolons
cat config.yaml | dasel -i yaml --root 'server.port = 9090; server.host = "0.0.0.0"' > config_tmp.yaml && mv config_tmp.yaml config.yaml
```

## Format Conversion

Pipe through dasel with different input/output format flags:

```bash
# JSON to YAML
cat data.json | dasel -i json -o yaml > data.yaml

# YAML to TOML
cat config.yaml | dasel -i yaml -o toml > config.toml

# JSON to XML
cat data.json | dasel -i json -o xml > data.xml

# TOML to JSON
cat config.toml | dasel -i toml -o json > config.json

# CSV to JSON
cat data.csv | dasel -i csv -o json > data.json
```

## Array Operations

### Append to Array

```bash
# Add element to end of array
echo '[1,2,3]' | dasel -i json --root '[$this..., 4]'
# Output: [1, 2, 3, 4]

# Append object to array
cat data.json | dasel -i json --root 'items = [$root.items..., {"name": "new", "value": 42}]'
```

### Batch Update with each

```bash
# Multiply all prices by 1.1 (10% increase)
cat data.json | dasel -i json --root 'items.each(price = price * 1.1)'

# Set a flag on all elements
cat data.json | dasel -i json --root 'users.each(active = true)'

# Increment all values
echo '[1,2,3]' | dasel -i json --root 'each($this = $this + 1)'
```

### Filter Then Transform

```bash
# Get only active users, then extract names
cat data.json | dasel -i json 'users.filter(active == true).map(name)'
```

## Object Operations

### Merge via Spread

```bash
# Add new key to existing object
cat base.json | dasel -i json --root '{ $root..., "newKey": "value" }'

# Merge two objects
cat base.json | dasel -i json --root '{ $root..., "extra": true, "version": 2 }'
```

### Field Deletion via Reconstruction

Since v3 has no `delete` command, remove fields by constructing a new object with only the desired keys:

```bash
# Keep only "name" and "email", drop everything else
echo '{"name":"a","email":"b","password":"c"}' | dasel -i json --root '{ name, email }'
```

### Field Rename via Reconstruction

```bash
echo '{"old_name": "value"}' | dasel -i json --root '{ "new_name": old_name }'
```

## Multi-Step Transformations

Use variable assignment and semicolons for complex operations:

```bash
# Store intermediate result in variable, then transform
cat data.json | dasel -i json '$active = users.filter(active == true); $active.map(name)'

# Multiple variables
cat data.json | dasel -i json '$a = items.filter(price > 100); $b = $a.map(name); $b'
```

## Conditional Transformation

```bash
# Set value based on condition
cat data.json | dasel -i json --root 'if(count > 5) { status = "many" } else { status = "few" }'
```

## Transformation Patterns

For detailed per-use-case transformation patterns (config updates, batch processing, format migration, data reshaping, error handling), see [Transformation Patterns](./references/transformation-patterns.md).

## References

- [Dasel v3 Documentation](https://daseldocs.tomwright.me) (fetched 2026-02-19)
- [Dasel Spread Operator](https://daseldocs.tomwright.me/syntax/spread.md) (fetched 2026-02-19)
- [Dasel each() Function](https://daseldocs.tomwright.me/functions/each.md) (fetched 2026-02-19)
- [Dasel filter() Function](https://daseldocs.tomwright.me/functions/filter.md) (fetched 2026-02-19)
- [Dasel CHANGELOG](https://raw.githubusercontent.com/TomWright/dasel/master/CHANGELOG.md) (fetched 2026-02-19)
