# Format-Specific Exploration Recipes

Per-format commands for exploring structured data with dasel v3. Each section covers the format's unique characteristics and provides concrete commands.

## Table of Contents

- [JSON Exploration](#json-exploration)
- [YAML Exploration](#yaml-exploration)
- [TOML Exploration](#toml-exploration)
- [XML Exploration](#xml-exploration)
- [CSV Exploration](#csv-exploration)
- [HCL Exploration](#hcl-exploration)
- [INI Exploration](#ini-exploration)

---

## JSON Exploration

JSON is dasel's native format. All operations work without caveats.

### Discover Structure

```bash
# Top-level keys
cat data.json | dasel -i json 'keys($this)'

# Nested object keys
cat data.json | dasel -i json 'keys(config.database)'
```

### Inspect Arrays of Objects

```bash
# Preview first element to understand object shape
cat data.json | dasel -i json 'users[0]'

# Keys of first element (reveals schema of array items)
cat data.json | dasel -i json 'keys(users[0])'

# Count elements
cat data.json | dasel -i json 'len(users)'

# Sample first 3 elements
cat data.json | dasel -i json 'users[0:3]'
```

### Search Nested Objects

```bash
# Find all objects containing "email" at any depth
cat data.json | dasel -i json 'search(has("email"))'

# Find objects where "status" equals "active"
cat data.json | dasel -i json 'search(status == "active")'

# Combined predicate
cat data.json | dasel -i json 'search(has("id") && has("name"))'
```

### Extract Specific Fields from Arrays

```bash
# Get all names from users array
cat data.json | dasel -i json 'users.map(name)'

# Get all unique roles
cat data.json | dasel -i json 'users.map(role)' | dasel -i json '$this...' | sort -u
```

### Mixed-Type Detection

```bash
# Check type of ambiguous field
cat data.json | dasel -i json 'typeOf(config.port)'
# Returns: "int", "string", "float", etc.

# Check if field is array or object
cat data.json | dasel -i json 'typeOf(metadata)'
```

---

## YAML Exploration

YAML supports anchors, multi-document files, and deep nesting common in Kubernetes and CI configs.

### Discover Structure

```bash
# Top-level keys
cat config.yaml | dasel -i yaml 'keys($this)'

# Deeply nested config (common in Kubernetes)
cat deployment.yaml | dasel -i yaml 'keys(spec.template.spec)'
```

### Deep Nesting Navigation

```bash
# Step through Kubernetes manifest
cat deployment.yaml | dasel -i yaml 'keys($this)'
# -> ["apiVersion", "kind", "metadata", "spec"]

cat deployment.yaml | dasel -i yaml 'keys(spec)'
# -> ["replicas", "selector", "template"]

cat deployment.yaml | dasel -i yaml 'spec.template.spec.containers[0].image'
```

### Inspect Nested Arrays

```bash
# List container names in a pod spec
cat deployment.yaml | dasel -i yaml 'spec.template.spec.containers.map(name)'

# Count containers
cat deployment.yaml | dasel -i yaml 'len(spec.template.spec.containers)'

# Get all environment variable names from first container
cat deployment.yaml | dasel -i yaml 'spec.template.spec.containers[0].env.map(name)'
```

### Recursive Key Search

```bash
# Find all keys named "image" at any depth
cat deployment.yaml | dasel -i yaml '..image'

# Find all objects with a "name" field
cat deployment.yaml | dasel -i yaml 'search(has("name"))'
```

---

## TOML Exploration

TOML uses tables (sections) and arrays of tables. Common in Rust (Cargo.toml), Python (pyproject.toml), and Go configs.

### Enumerate Tables

```bash
# Top-level tables and keys
cat pyproject.toml | dasel -i toml 'keys($this)'

# Nested tables
cat Cargo.toml | dasel -i toml 'keys(dependencies)'
cat pyproject.toml | dasel -i toml 'keys(tool.ruff)'
```

### Inspect Arrays of Tables

```bash
# pyproject.toml optional-dependencies or similar array sections
cat Cargo.toml | dasel -i toml 'keys(bin[0])'
cat Cargo.toml | dasel -i toml 'len(bin)'
```

### Value Extraction

```bash
# Package metadata
cat pyproject.toml | dasel -i toml 'project.name'
cat pyproject.toml | dasel -i toml 'project.version'

# Dependency list
cat pyproject.toml | dasel -i toml 'keys(project.dependencies)'
```

### Type Checking

```bash
# Verify field types (TOML distinguishes int, float, string, bool, datetime)
cat config.toml | dasel -i toml 'typeOf(server.port)'
cat config.toml | dasel -i toml 'typeOf(server.debug)'
```

---

## XML Exploration

XML has elements, attributes, and text content. Dasel represents these as nested objects.

### Element Listing

```bash
# Top-level element (XML has single root)
cat data.xml | dasel -i xml 'keys($this)'

# Child elements
cat pom.xml | dasel -i xml 'keys(project)'
cat pom.xml | dasel -i xml 'keys(project.dependencies)'
```

### Inspect Repeated Elements

```bash
# Count dependency entries in Maven POM
cat pom.xml | dasel -i xml 'len(project.dependencies.dependency)'

# First dependency
cat pom.xml | dasel -i xml 'project.dependencies.dependency[0]'
```

### Attribute Access

XML attributes are accessible as properties on the element. The exact representation depends on dasel's XML mapping. Inspect the element first:

```bash
# View full element to see attribute representation
cat data.xml | dasel -i xml 'root.element[0]'
```

### Recursive Search

```bash
# Find all elements with a specific child
cat data.xml | dasel -i xml 'search(has("version"))'
```

---

## CSV Exploration

CSV files are represented as arrays of objects (header row becomes keys).

### Header Extraction

```bash
# Get column names from first row
cat data.csv | dasel -i csv 'keys($this[0])'
```

### Row Count

```bash
cat data.csv | dasel -i csv 'len($this)'
```

### Sample Rows

```bash
# First row (as object with column keys)
cat data.csv | dasel -i csv '$this[0]'

# First 3 rows
cat data.csv | dasel -i csv '$this[0:3]'
```

### Column Sampling

```bash
# Extract single column values
cat data.csv | dasel -i csv '$this.map(name)'

# Unique values in a column
cat data.csv | dasel -i csv '$this.map(category)' | dasel -i json '$this...' | sort -u
```

### Type Inspection

CSV values are typically strings. Check with:

```bash
cat data.csv | dasel -i csv 'typeOf($this[0].age)'
```

---

## HCL Exploration

HCL (HashiCorp Configuration Language) uses blocks with labels. Common in Terraform files.

### Block Discovery

```bash
# Top-level block types
cat main.tf | dasel -i hcl 'keys($this)'
# -> ["resource", "variable", "output", "provider"]
```

### Inspect Block Labels

```bash
# Resource types
cat main.tf | dasel -i hcl 'keys(resource)'

# Specific resource
cat main.tf | dasel -i hcl 'resource.aws_instance'
cat main.tf | dasel -i hcl 'keys(resource.aws_instance)'
```

### Nested Block Inspection

```bash
# Terraform resource attributes
cat main.tf | dasel -i hcl 'resource.aws_instance.web'
cat main.tf | dasel -i hcl 'keys(resource.aws_instance.web)'
```

### Variable Discovery

```bash
# List all variable names
cat variables.tf | dasel -i hcl 'keys(variable)'

# Get variable default value
cat variables.tf | dasel -i hcl 'variable.region.default'
```

---

## INI Exploration

INI files have sections and key-value pairs. Common in systemd, PHP, Git config.

### Section Listing

```bash
# List all sections
cat config.ini | dasel -i ini 'keys($this)'
```

### Key Listing Within Section

```bash
# Keys in a specific section
cat config.ini | dasel -i ini 'keys(database)'
cat config.ini | dasel -i ini 'keys(server)'
```

### Value Extraction

```bash
cat config.ini | dasel -i ini 'database.host'
cat config.ini | dasel -i ini 'server.port'
```

### Full Section Dump

```bash
# View all keys and values in a section
cat config.ini | dasel -i ini 'database'
```

---

## Cross-Format Tips

- **Type ambiguity**: CSV and INI store everything as strings. Use `typeOf()` to confirm before numeric operations.
- **XML root**: XML always has exactly one root element. `keys($this)` returns a single-element array.
- **TOML datetimes**: TOML natively supports datetime types. `typeOf()` reports these distinctly.
- **HCL labels**: HCL block labels become nested object keys. `resource.aws_instance.web` navigates type -> label -> label.
- **Large files**: Use `search()` instead of recursive descent (`..`) when you need predicate-based filtering, not exhaustive traversal.

## References

- [Dasel Query Syntax](https://daseldocs.tomwright.me/syntax/query-syntax.md) (fetched 2026-02-19)
- [Dasel Functions Index](https://daseldocs.tomwright.me/functions) (fetched 2026-02-19)
- [Dasel Arrays and Slices](https://daseldocs.tomwright.me/syntax/arrays-slices.md) (fetched 2026-02-19)
