---
name: enterprise-maven-pom
description: Dasel v3 selector patterns for Maven POM XML files — use when querying dependency versions, filtering by groupId or scope, extracting module hierarchy from parent POMs, or detecting version conflicts across enterprise multi-module Java projects. Load this skill when working with pom.xml files using dasel.
---

# Maven POM Query Patterns

<when_to_use>

Load this skill when querying any `pom.xml` file — extracting dependency versions, filtering by groupId or scope, mapping module hierarchy from parent POMs, or detecting version conflicts across a multi-module Java project.

</when_to_use>

Domain skill for querying Maven POM XML files using dasel v3. Always pass `-i xml` explicitly. Child element text content (groupId, artifactId, version, scope) is accessed by element name directly — no `#text` needed. Write intermediate batch results to `/tmp/`, never to the source tree.

## Dependency Extraction

```bash
# All dependency groupIds from a single POM
cat pom.xml | dasel -i xml 'project.dependencies.dependency.map(groupId)'
```

## Framework Version Filtering

Filter dependencies by groupId to isolate framework-specific versions.

```bash
# Spring dependency versions
cat pom.xml | dasel -i xml 'project.dependencies.dependency.filter(groupId == "org.springframework").map(version)'

# Hibernate dependency versions
cat pom.xml | dasel -i xml 'project.dependencies.dependency.filter(groupId == "org.hibernate").map(version)'
```

## Scope Filtering

```bash
# Test-scoped dependency artifactIds
cat pom.xml | dasel -i xml 'project.dependencies.dependency.filter(scope == "test").map(artifactId)'

# Compile-scoped dependencies (no scope element defaults to compile)
cat pom.xml | dasel -i xml 'project.dependencies.dependency.filter(scope == "compile").map(artifactId)'
```

## Module Hierarchy

Extract module paths from a parent POM to map the project structure.

```bash
# Module list from parent POM
cat pom.xml | dasel -i xml 'project.modules.module'
```

## Cross-POM Version Conflict Detection

Batch pattern — iterate all POMs, extract dependencies per file, compare. Write results to `/tmp/`.

```bash
# Collect all dependency groupIds across every POM in the hierarchy
for pom in $(fdfind -e xml -n pom.xml .); do
  echo "=== $pom ===" >> /tmp/all_deps.txt
  cat "$pom" | dasel -i xml 'project.dependencies.dependency.map(groupId)' >> /tmp/all_deps.txt 2>/dev/null
done
```

Inspect `/tmp/all_deps.txt` for the same groupId appearing with different versions across modules.

## Multi-Field Extraction

Extract groupId and artifactId together for dependency inventory.

```bash
# Dependency coordinates (groupId + artifactId) — run as two passes
cat pom.xml | dasel -i xml 'project.dependencies.dependency.map(groupId)'
cat pom.xml | dasel -i xml 'project.dependencies.dependency.map(artifactId)'
```

## DependencyManagement vs Dependencies

Enterprise POMs use `dependencyManagement` to declare BOM-controlled versions separately from active `dependencies`.

```bash
# Managed dependency versions (BOM section)
cat pom.xml | dasel -i xml 'project.dependencyManagement.dependencies.dependency.map(version)'

# Active dependency versions (may be empty if version comes from BOM)
cat pom.xml | dasel -i xml 'project.dependencies.dependency.map(version)'
```
