---
name: data-exploration
description: Use when exploring unknown structured data files with dasel v3 — discover schema, list keys, find nested values, sample arrays, identify data types across JSON, YAML, TOML, XML, CSV, HCL, INI formats
---

# Data Exploration with Dasel v3

<when_to_use>

Activate this skill when:

- Exploring unfamiliar structured data files (config, API responses, datasets)
- Discovering the schema or shape of a document before modifying it
- Investigating nested config structures (Kubernetes manifests, CI pipelines, package files)
- Sampling large arrays or deeply nested objects to understand content
- Identifying data types before transformation or extraction

</when_to_use>

## Supported Formats

Dasel auto-detects format from file extension. Override with `-i <format>` when reading from stdin or when extension is ambiguous.

Format identifiers: `json`, `yaml`, `toml`, `xml`, `csv`, `hcl`, `ini`

## Universal Exploration Workflow

Follow this sequence when encountering an unknown structured data file. Each step narrows scope.

### Step 1 — Format Detection

Dasel infers format from file extension. For stdin or non-standard extensions, specify explicitly:

```bash
cat mystery_file | dasel -i json 'keys($this)'
```

### Step 2 — Top-Level Keys

```bash
cat config.yaml | dasel -i yaml 'keys($this)'
```

Output: array of top-level key names. This is always the first exploration command.

### Step 3 — Structure Preview

For small files (configs, manifests), dump the full document:

```bash
cat config.yaml | dasel -i yaml
```

For large files, skip to Step 4.

### Step 4 — Nested Key Discovery

Navigate level by level:

```bash
cat config.yaml | dasel -i yaml 'server'
cat config.yaml | dasel -i yaml 'keys(server)'
cat config.yaml | dasel -i yaml 'keys(server.logging)'
```

Recursive key discovery across all depths:

```bash
cat config.yaml | dasel -i yaml '..keys($this)'
```

### Step 5 — Array Sampling

Preview first few elements without loading entire array:

```bash
cat data.json | dasel -i json 'items[0:3]'
```

Single element inspection:

```bash
cat data.json | dasel -i json 'items[0]'
```

### Step 6 — Type Inspection

Determine the type of any node:

```bash
cat data.json | dasel -i json 'typeOf(settings)'
cat data.json | dasel -i json 'typeOf(items[0].count)'
```

Return values: `"string"`, `"array"`, `"bool"`, `"null"`, `"int"`, `"float"`

### Step 7 — Value Extraction

Once path is known, extract specific values:

```bash
cat config.yaml | dasel -i yaml 'database.connection.host'
cat data.json | dasel -i json 'users[0].email'
```

## Exploration Patterns

### Breadth-First Exploration

Start at root, enumerate keys at each level before going deeper:

```bash
cat file.json | dasel -i json 'keys($this)'           # Level 0
cat file.json | dasel -i json 'keys(metadata)'         # Level 1
cat file.json | dasel -i json 'keys(metadata.labels)'  # Level 2
```

### Search-Based Exploration (Large Files)

When the file is too large for manual traversal, use `search()` with predicates:

```bash
# Find all objects containing a specific key
cat data.json | dasel -i json 'search(has("email"))'

# Find all objects with both "id" and "name" keys
cat data.json | dasel -i json 'search(has("id") && has("name"))'

# Find nodes where a value matches
cat data.json | dasel -i json 'search($this == 42)'
```

### Count Elements

```bash
cat data.json | dasel -i json 'len(items)'
cat data.json | dasel -i json 'len(keys($this))'
```

### Unique Value Discovery

Extract a field from all array elements, then deduplicate in shell:

```bash
cat data.json | dasel -i json 'items.map(category)' | dasel -i json '$this...' | sort -u
```

### Recursive Descent

Find all values for a key name at any depth:

```bash
cat data.json | dasel -i json '..name'
```

Get first element of every nested array:

```bash
cat data.json | dasel -i json '..[0]'
```

## Format-Specific Recipes

For detailed per-format exploration commands, see [Format-Specific Recipes](./references/format-recipes.md).

## References

- [Dasel v3 Documentation](https://daseldocs.tomwright.me) (fetched 2026-02-19)
- [Dasel Functions Index](https://daseldocs.tomwright.me/functions) (fetched 2026-02-19)
- [Dasel GitHub Repository](https://github.com/TomWright/dasel) (fetched 2026-02-19)
