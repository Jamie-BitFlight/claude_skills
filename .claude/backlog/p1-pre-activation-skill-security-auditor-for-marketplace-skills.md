---
name: Pre-activation skill security auditor for marketplace skills
description: "## Current state\n\n`plugin_validator.py` validates structural concerns: YAML frontmatter schema, token complexity, internal link validity, plugin.json compliance, and progressive disclosure structure. It does not scan skill content for security risks such as command injection patterns in scripts, data exfiltration vectors in hook commands, prompt injection in SKILL.md body text, or privilege escalation via `allowed-tools` overgrants. No security-focused validation exists anywhere in the plugin-creator pipeline."
metadata:
  topic: pre-activation-skill-security-auditor-for-marketplace-skills
  source: 'Research entry: ./research/skill-generation-tools/claude-code-skills-alirezarezvani.md -- pattern: skill-security-auditor scanning before activation'
  added: '2026-03-10'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#559'
  last_synced: '2026-03-21T08:07:50Z'
---

## Story

As a **developer using Claude Code skills**, I want to **pre-activation skill security auditor for marketplace skills** so that **the tooling becomes more capable and complete**.

## Description

## Current state

`plugin_validator.py` validates structural concerns: YAML frontmatter schema, token complexity, internal link validity, plugin.json compliance, and progressive disclosure structure. It does not scan skill content for security risks such as command injection patterns in scripts, data exfiltration vectors in hook commands, prompt injection in SKILL.md body text, or privilege escalation via `allowed-tools` overgrants. No security-focused validation exists anywhere in the plugin-creator pipeline.

## Target state

A `scripts/skill_security_auditor.py` script (or new validator pass in `plugin_validator.py`) scans skill packages before marketplace publication or installation. Checks include: (1) scripts/ files scanned for `subprocess.call(shell=True)`, `os.system()`, `eval()`, `exec()` patterns; (2) hook commands in frontmatter checked for shell injection vectors (unquoted variables, pipe chains to external URLs); (3) SKILL.md body checked for prompt injection markers (instructions to ignore previous instructions, hidden system prompts); (4) `allowed-tools` field checked against a deny-list of dangerous tool combinations (e.g., `Bash(*)` without constraints). Each finding classified as PASS/WARN/FAIL with remediation text.

## Measurable signal

Run: `uv run plugins/plugin-creator/scripts/skill_security_auditor.py plugins/plugin-creator/skills/skill-creator/` -- output includes a verdict (PASS/WARN/FAIL) and a findings list. Script exits 0 on PASS, 1 on WARN, 2 on FAIL. At least the four scan categories above are present in the output JSON.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Research entry: ./research/skill-generation-tools/claude-code-skills-alirezarezvani.md -- pattern: skill-security-auditor scanning before activation
- **Priority**: P1
- **Added**: 2026-03-10
- **Research questions**: None
