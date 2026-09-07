# Development Harness Purpose

**Audience**: Mixed overview. Use this document to orient contributors and agents to the logical
product contract; follow linked contributor references for implementation detail.

This document states what the harness is for. How it achieves that — the automation boundary,
the logical work model, and the frontend and backend contracts — is in
[ARCHITECTURE.md](../ARCHITECTURE.md).

## Purpose

Development Harness targets a generic agent work-management system that
preserves logical work and the evidence needed to move it from intake to
validated closure.

The plugin is primarily an agent-facing workflow system expressed in Markdown.
Skills and reference documents carry the reasoning process; scripts, hooks,
CLI commands, and MCP tools remove repeatable mechanics and provide stable
interfaces between stages.

## Documentation Frames and Audiences

Development Harness documentation has two primary frames. A document must make
its frame clear and include only the detail needed by that audience.

### Contributor and developer frame

This frame explains how the plugin and its workflow are designed, implemented,
extended, tested, and operated as a software system. It includes:

- workflow and package architecture;
- Markdown skill, command, agent, and reference composition;
- Python modules and PEP 723 script entry points;
- MCP and CLI transport boundaries;
- hooks and agent-event integration;
- provider protocols, cache ownership, and persistence design;
- `uv` runtime, dependency, test, lint, and packaging requirements; and
- contributor troubleshooting that requires tracing implementation behavior.

Its primary audience is an AI agent changing or diagnosing the plugin. These
documents must understand the consumer workflow so implementation preserves
observable behavior, but they may expose internal structure where that is
necessary for correct engineering.

### Installation, configuration, and usage frame

This frame explains how an agent installs, configures, uses, and troubleshoots
the plugin through its supported capabilities. It describes logical workflows,
inputs, outputs, configuration choices, supported provider behavior, failure
messages, and recovery actions.

Consumer documents do not teach internal implementation unless a detail is
required to configure the plugin, interpret behavior, or perform a bounded
troubleshooting trace. They refer to logical operations and supported tool
surfaces rather than Python modules, cache files, provider wire formats, or
internal call graphs.

### Audience rule

Almost all plugin documentation is written for AI agents. The plugin README and
a small set of overview or selection documents are the exception: they serve
both humans evaluating the plugin and agents orienting themselves. Those mixed-
audience documents use plain capability and workflow language, with links to
agent-facing operational or contributor references for depth.

Contributor documentation may depend on consumer documentation to understand
the product contract. Consumer documentation must not require contributor
documentation for ordinary installation, configuration, usage, or recovery.

## Closed-Loop Work Management

The system is intended to support a full closed loop:

1. Intake a backlog item and groom its scope and evidence.
2. Research and assess the existing system factually, then produce architecture.
3. Produce a plan.
4. Decompose work into atomic tasks; sequence, distribute, and coordinate them.
5. Execute tasks.
6. Append findings, workarounds, concerns, and validation evidence upstream.
7. Revise the plan, add tasks, or create a follow-up backlog item when evidence requires it.
8. Review the plan and architecture.
9. Validate the product-level outcome, including documentation, tests, end-to-end checks, and CI when applicable.
10. Close work with evidence.

This model is domain-generic. It applies to software, Markdown agent and plugin
work, design, TUI, web, and font work, job search, research, ranking, and other
work that benefits from durable scope, relationships, coordination, and evidence.

