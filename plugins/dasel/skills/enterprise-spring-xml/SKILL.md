---
name: enterprise-spring-xml
description: Dasel v3 selectors for Spring bean factory XML — use when querying any Spring ApplicationContext XML for bean discovery, dependency wiring, JMS destination mapping, property injection extraction, or cross-bean reference tracing. Load this skill before writing dasel selectors against Spring bean XML files (applicationContext.xml, *_beans.xml, spring-*.xml).
---

# Spring Bean Factory XML — Dasel v3 Query Patterns

<when_to_use>

Load this skill when querying any Spring bean XML file — `applicationContext.xml`, `*_beans.xml`, `spring-context.xml`, or any Spring ApplicationContext XML — for bean discovery, dependency analysis, JMS wiring, property injection auditing, or cross-bean reference tracing.

</when_to_use>

Dasel v3 selector patterns for Spring bean factory XML. Always pass `-i xml` explicitly.

**Attribute prefix rule:** Dasel friendly mode (default) prefixes XML attributes with `-`. The `id` attribute is `-id`, `class` is `-class`. Text content is `#text`.

## Bean Discovery

```bash
# All bean IDs
cat chaosrouter_beans.xml | dasel -i xml 'beans.bean.filter(has("-id")).map("-id")'

# All bean classes
cat chaosrouter_beans.xml | dasel -i xml 'beans.bean.filter(has("-class")).map("-class")'

# Map -class across every bean (includes beans without -id)
cat chaosrouter_beans.xml | dasel -i xml 'beans.bean.map("-class")'
```

## Class Pattern Matching

Filter beans by class name via regex on `-class`.

```bash
# Beans whose class contains JmsTemplate
cat chaosrouter_beans.xml | dasel -i xml 'beans.bean.filter(-class ~ ".*JmsTemplate.*").map("-id")'

# Count beans matching a class pattern
cat beans.xml | dasel -i xml 'len(beans.bean.filter(-class ~ ".*Jms.*"))'
```

## Dependency Wiring Analysis

Find beans referencing other beans via the `-ref` attribute on `property` child elements.

**Pattern:** `parentCollection.filter(childElement.filter(condition).len($this) > 0)` — filters the parent by testing whether a matching child exists (length > 0).

```bash
# Beans that reference a specific bean ID via ref attribute
cat chaosrouter_beans.xml | dasel -i xml 'beans.bean.filter(property.filter(-ref == "targetBeanId").len($this) > 0).map("-id")'
```

## JMS Destination Mapping

Find which beans consume which JMS destinations via `property` child elements.

```bash
# Beans wired to a specific destination property
cat integrationpoint_beans.xml | dasel -i xml 'beans.bean.filter(property.filter(-name == "destination").len($this) > 0).map("-id")'
```

## Property Injection Extraction

Extract externalized `${...}` placeholder values from bean definitions.

```bash
# All property values using ${...} placeholders
cat storage_beans.xml | dasel -i xml 'beans.bean.property.filter(-value ~ ".*\\$\\{.*\\}.*").map("-value")'
```

## Attribute and Text Content Access

```bash
# <bean id="myBean" class="com.example.Foo">some text</bean>
cat beans.xml | dasel -i xml 'beans.bean[0].-id'       # myBean
cat beans.xml | dasel -i xml 'beans.bean[0].-class'    # com.example.Foo
cat beans.xml | dasel -i xml 'beans.bean[0].#text'     # some text

# Discover all keys (attributes + child elements) on first bean
cat beans.xml | dasel -i xml 'beans.bean[0].keys($this)'
```

## Namespace Handling

Friendly mode strips namespace prefixes from element names — works for most Spring queries.

When namespace prefixes cause selector failures (element not found despite existing), switch to structured mode:

```bash
cat spring-context.xml | dasel -i xml --read-flag xml-mode=structured 'beans.bean[0]'
```

## Cross-File Analysis

Write intermediate results to `/tmp/` — never to the source tree.

```bash
# Extract bean IDs from multiple files, compare
cat chaosrouter_beans.xml | dasel -i xml 'beans.bean.filter(has("-id")).map("-id")' > /tmp/chaosrouter_beans.txt
cat integrationpoint_beans.xml | dasel -i xml 'beans.bean.filter(has("-id")).map("-id")' > /tmp/integration_beans.txt
diff /tmp/chaosrouter_beans.txt /tmp/integration_beans.txt
```
