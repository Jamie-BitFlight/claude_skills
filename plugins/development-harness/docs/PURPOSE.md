# Development Harness Purpose

**Audience**: Mixed overview. Use this document to orient contributors and agents to the logical
product contract; follow linked contributor references for implementation detail.

This document states what the harness is for. How it achieves that — the automation boundary,
the logical work model, and the frontend and backend contracts — is in
[ARCHITECTURE.md](../ARCHITECTURE.md).

## Purpose

Development Harness targets a generic agent work-management system that
preserves logical work and the evidence needed to move it from creation to
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

## What the workflow must deliver

Stated as outcomes. The stages that produce them, what each reads and produces, and where they are
not yet implemented, are in [ARCHITECTURE.md](../ARCHITECTURE.md).

- A requirement, feature or defect is understood as part of the whole system before anyone designs
  for it.
- Claims are checked and corrected rather than carried forward, and the problem is considered from
  the right altitudes.
- A design holds up against the problems and scenarios the groomed item states, having been
  adversarially challenged rather than merely written.
- A plan makes its own achievement demonstrable — against the architecture, and against the problem
  statement it started from.
- Claims without evidence, and functional gaps, are surfaced back to the stages that can resolve
  them instead of being carried into the work.
- Work is split so that what may run concurrently does, and each piece carries a goal, guardrails,
  acceptance criteria, and a way to tell it is done.
- An agent doing a piece of work can reach the plan and the research that justifies it when it needs
  to, and is not told how to do the work in place of evidence it could test.
- New information found while working — a concern, a gap, an adjacent broken system, an
  environmental failure, a security issue — reaches whoever can act on it, and the plan and the work
  change in response.
- A completed change is reviewed in proportion to what changed, its documentation is updated, and
  its effectiveness at what it set out to achieve is demonstrated rather than asserted.
- Work closes with the evidence that it is done.

Each of these answers a failure met repeatedly in agentic engineering and AI co-working. An
assessment of this system that cannot say which outcome a defect belongs to has not understood it.

## Domain reach

Domain-generic, by construction. The harness orchestrates work; it does not perform it. It carries
scope, relationships, coordination and evidence, and what happens inside a unit of work belongs to
the agent doing it. So the domain arrives at runtime, with whatever is asked of it — the same way a
CI system is language-agnostic because it runs commands rather than compiling.

There is no implementation of software work here either. Asking where the harness implements font
work, a job search or a ranking exercise asks the wrong layer: it implements the loop, and the loop
is the same one whatever the work is.

A unit of work may be a change to a repository, and it may equally be the validation of an external
system — a UI test against a web page, a radio reading from a microcontroller — or work that
produces no repository artifact at all.

The default artifact-type vocabulary is named for code (`codebase-analysis`, `code-review`). That is
vocabulary in an extensible table, and it names the types a software project happens to register
first.

One constraint is real and it belongs to automation rather than to any domain: a structured
acceptance criterion carries an executable check command, so completion is decided by something a
machine can run. A CI job passes on an exit code whether it compiled a binary or sent an email;
what this excludes is work whose completion is a judgement rather than a check.
