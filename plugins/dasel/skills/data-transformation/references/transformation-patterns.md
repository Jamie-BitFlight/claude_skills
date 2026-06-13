# Transformation Patterns

Detailed dasel v3 patterns organized by use case. Each pattern follows the structure: problem, dasel command, expected result, caveats.

## Table of Contents

- [Config File Update Patterns](#config-file-update-patterns)
- [Batch Processing Patterns](#batch-processing-patterns)
- [Format Migration Patterns](#format-migration-patterns)
- [Data Reshaping Patterns](#data-reshaping-patterns)
- [Multi-File Operations](#multi-file-operations)
- [Error Handling](#error-handling)

---

## Config File Update Patterns

### YAML Config — Update Nested Values

**Problem**: Update a database host in a multi-level YAML config.

```bash
cat config.yaml | dasel -i yaml --root 'database.connection.host = "db-prod.example.com"' > tmp.yaml && mv tmp.yaml config.yaml
```

**Expected**: Full document output with only the target field changed.

### YAML Config — Add New Section

**Problem**: Add an entirely new top-level section.

```bash
cat config.yaml | dasel -i yaml --root '{ $root..., "monitoring": {"enabled": true, "port": 9090} }' > tmp.yaml && mv tmp.yaml config.yaml
```

**Expected**: Original document preserved with new `monitoring` section appended.

### TOML Settings — Modify Table Values

**Problem**: Update version in pyproject.toml.

```bash
cat pyproject.toml | dasel -i toml --root 'project.version = "2.0.0"' > tmp.toml && mv tmp.toml pyproject.toml
```

### TOML Settings — Add Array-of-Tables Entry

**Problem**: Add a new `[[tool.ruff.per-file-ignores]]` entry or similar array-of-tables.

```bash
cat pyproject.toml | dasel -i toml --root 'tool.ruff.per-file-ignores = [$root.tool.ruff.per-file-ignores..., {"pattern": "tests/**", "ignore": ["S101"]}]' > tmp.toml && mv tmp.toml pyproject.toml
```

**Caveat**: TOML array-of-tables have specific serialization rules. Verify output format matches TOML spec expectations.

### JSON Package Files — Update Version

**Problem**: Bump version in package.json.

```bash
cat package.json | dasel -i json --root 'version = "3.1.0"' > tmp.json && mv tmp.json package.json
```

### JSON Package Files — Add Dependency

**Problem**: Add a new dependency to package.json.

```bash
cat package.json | dasel -i json --root '{ $root..., "dependencies": { $root.dependencies..., "lodash": "^4.17.21" } }' > tmp.json && mv tmp.json package.json
```

---

## Batch Processing Patterns

### Map Over Arrays

**Problem**: Extract a derived field from each element.

```bash
# Get full names from objects with firstName and lastName
cat users.json | dasel -i json 'users.map({ "full": firstName })'
```

### Filter Then Transform

**Problem**: Find expensive items and apply a discount.

```bash
# Chain filter + each
cat products.json | dasel -i json --root '$expensive = products.filter(price > 100); $expensive.each(price = price * 0.9)'
```

**Caveat**: The `each` mutates in the query context. Use `--root` to get the full document with changes applied.

### Batch Update with each

**Problem**: Set all users to inactive.

```bash
cat data.json | dasel -i json --root 'users.each(active = false)'
```

**Expected**: Every element in the `users` array has `active` set to `false`.

### Batch Numeric Update

**Problem**: Increase all prices by 15%.

```bash
cat catalog.json | dasel -i json --root 'items.each(price = price * 1.15)'
```

### Conditional Batch Update

**Problem**: Set status based on a threshold.

```bash
cat data.json | dasel -i json --root 'items.each(status = if(score > 80) { "pass" } else { "fail" })'
```

---

## Format Migration Patterns

### JSON to YAML

```bash
cat data.json | dasel -i json -o yaml > data.yaml
```

**Caveats**: Clean conversion. No data loss. YAML output uses dasel's default indentation (2 spaces).

### YAML to TOML

```bash
cat config.yaml | dasel -i yaml -o toml > config.toml
```

**Caveats**:
- YAML anchors and aliases are resolved before conversion (dasel reads the resolved document)
- YAML multi-document files (`---` separator) are not supported; only the first document is processed
- Null values in YAML may not have a TOML equivalent

### JSON to XML

```bash
cat data.json | dasel -i json -o xml > data.xml
```

**Caveats**:
- XML requires a single root element. If JSON has multiple top-level keys, dasel wraps them in a root element
- JSON arrays map to repeated XML elements
- JSON null values may serialize as empty elements

### CSV to JSON

```bash
cat data.csv | dasel -i csv -o json > data.json
```

**Caveats**:
- CSV header row becomes object keys
- All CSV values are strings; numeric conversion requires post-processing
- Empty cells become empty strings, not null

### TOML to JSON

```bash
cat config.toml | dasel -i toml -o json > config.json
```

**Caveats**: TOML datetime types serialize as ISO 8601 strings in JSON.

### Conversion Caveats Summary

| Source | Target | Caveats |
|--------|--------|---------|
| JSON | YAML | None |
| YAML | TOML | Anchors resolved; nulls may fail; multi-doc unsupported |
| JSON | XML | Root element auto-added; arrays become repeated elements |
| CSV | JSON | All values are strings; no null representation |
| TOML | JSON | Datetimes become ISO 8601 strings |
| XML | JSON | Attributes and text nodes become special keys |
| HCL | JSON | Block labels become nested keys |
| INI | JSON | All values are strings; no nested structure |

---

## Data Reshaping Patterns

### Flatten Nested to Flat

**Problem**: Extract nested fields into a flat structure.

```bash
# From: {"user": {"name": "Alice", "address": {"city": "NYC"}}}
# To:   {"name": "Alice", "city": "NYC"}
echo '{"user":{"name":"Alice","address":{"city":"NYC"}}}' | \
  dasel -i json --root '{"name": user.name, "city": user.address.city}'
```

### Nest Flat to Nested

**Problem**: Group flat fields into nested structure.

```bash
# From: {"db_host": "localhost", "db_port": 5432}
# To:   {"db": {"host": "localhost", "port": 5432}}
echo '{"db_host":"localhost","db_port":5432}' | \
  dasel -i json --root '{"db": {"host": db_host, "port": db_port}}'
```

### Extract Subset

**Problem**: Pull out only specific fields from a large document.

```bash
cat large.json | dasel -i json '{ name, version, description }'
```

### Array to Object Mapping

**Problem**: Transform array of key-value pairs to an object.

```bash
# Use map to extract, then reconstruct
cat data.json | dasel -i json 'settings.map({ key, value })'
```

---

## Multi-File Operations

### Shell Loop for Batch File Updates

**Problem**: Update a field across multiple YAML files.

```bash
for f in configs/*.yaml; do
  cat "$f" | dasel -i yaml --root 'metadata.version = "2.0"' > "${f}.tmp" && mv "${f}.tmp" "$f"
done
```

### Convert Directory of JSON to YAML

```bash
for f in data/*.json; do
  cat "$f" | dasel -i json -o yaml > "${f%.json}.yaml"
done
```

### Extract Same Field from Multiple Files

```bash
for f in services/*/config.yaml; do
  echo "$f: $(cat "$f" | dasel -i yaml 'service.port')"
done
```

---

## Error Handling

### Common Transformation Errors

**Error**: `unknown key: fieldname`

**Cause**: The field path does not exist in the document.

**Fix**: Verify path with exploration commands first:

```bash
cat data.json | dasel -i json 'keys($this)'
cat data.json | dasel -i json 'has("fieldname")'
```

**Error**: `cannot use X as type Y`

**Cause**: Assigning a value of wrong type (e.g., string to integer field).

**Fix**: Use type casting functions:

```bash
cat data.json | dasel -i json --root 'port = toInt("9090")'
```

**Error**: `expected array, got object` (or vice versa)

**Cause**: Path points to different type than expected.

**Fix**: Check type before operating:

```bash
cat data.json | dasel -i json 'typeOf(items)'
```

**Error**: Truncated/empty output file

**Cause**: Redirected output to the same input file (`> same-file`).

**Fix**: Always use temp file + rename pattern:

```bash
cat input.json | dasel -i json --root '...' > tmp.json && mv tmp.json input.json
```

### Defensive Transformation Pattern

For critical files, validate before overwriting:

```bash
# 1. Transform to temp
cat config.yaml | dasel -i yaml --root 'server.port = 9090' > config_new.yaml

# 2. Verify temp is valid (non-empty, parseable)
cat config_new.yaml | dasel -i yaml 'keys($this)' > /dev/null && mv config_new.yaml config.yaml || echo "Transformation produced invalid output"
```

### Dry Run Pattern

Preview transformation without writing:

```bash
# Just print — do not redirect
cat config.yaml | dasel -i yaml --root 'server.port = 9090'
```

Inspect the output. If correct, re-run with redirect.

---

## Variable and Multi-Statement Patterns

### Complex Transformations with Variables

```bash
# Store filtered subset, then transform
cat data.json | dasel -i json '$active = users.filter(active == true); $names = $active.map(name); $names'
```

### Passing External Variables

Use `--var` to inject values from the shell:

```bash
VERSION="3.0.0"
cat package.json | dasel -i json --var "v=$VERSION" --root 'version = $v' > tmp.json && mv tmp.json package.json
```

### Chaining with Shell Pipes

```bash
# Read JSON, transform, convert to YAML
cat data.json | dasel -i json --root 'items.each(processed = true)' | dasel -i json -o yaml > output.yaml
```

## References

- [Dasel Spread Syntax](https://daseldocs.tomwright.me/syntax/spread.md) (fetched 2026-02-19)
- [Dasel Conditionals](https://daseldocs.tomwright.me/syntax/conditionals.md) (fetched 2026-02-19)
- [Dasel each()](https://daseldocs.tomwright.me/functions/each.md) (fetched 2026-02-19)
- [Dasel filter()](https://daseldocs.tomwright.me/functions/filter.md) (fetched 2026-02-19)
- [Dasel map()](https://daseldocs.tomwright.me/functions/map.md) (fetched 2026-02-19)
- [Dasel CHANGELOG](https://raw.githubusercontent.com/TomWright/dasel/master/CHANGELOG.md) (fetched 2026-02-19)
