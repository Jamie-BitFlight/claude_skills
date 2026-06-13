---
name: enterprise-tomcat-web
description: Dasel v3 patterns for querying Tomcat web.xml deployment descriptors — use when inspecting servlet enumeration, filter chain discovery, listener listing, context parameter extraction, or init-param inspection in web.xml files
---

# Tomcat web.xml Dasel Query Patterns

<when_to_use>

Load this skill when querying a `web.xml` deployment descriptor — enumerating servlets, inspecting filter chains, listing listeners, extracting context parameters, or finding servlets by init-param value.

</when_to_use>

Domain skill for querying Tomcat web.xml files using dasel v3. Always use `-i xml` explicitly. XML attributes use `-` prefix in dasel friendly mode.

## Servlet Discovery

```bash
# All servlet names
cat web.xml | dasel -i xml 'web-app.servlet.map(servlet-name)'

# Count servlet definitions
cat web.xml | dasel -i xml 'len(web-app.servlet)'
```

## Filter Chain Analysis

```bash
# Find filters by class pattern (e.g., Security filters)
cat web.xml | dasel -i xml 'web-app.filter.filter(filter-class ~ ".*Security.*")'
```

Replace `Security` with any class name fragment.

## Listener Enumeration

```bash
# Count listener definitions
cat web.xml | dasel -i xml 'len(web-app.listener)'
```

## Context Parameters

```bash
# All context-param names
cat web.xml | dasel -i xml 'web-app.context-param.map(param-name)'
```

## Init Parameter Inspection

```bash
# Find servlets with a specific init-param name — filters parent collection by testing child length > 0
cat web.xml | dasel -i xml 'web-app.servlet.filter(init-param.filter(param-name == "debug").len($this) > 0).map(servlet-name)'
```

Replace `"debug"` with the target param-name value.

All selectors require the full command prefix: `cat web.xml | dasel -i xml '<selector>'`
