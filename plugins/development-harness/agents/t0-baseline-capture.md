---
name: t0-baseline-capture
description: Captures baseline state of structured acceptance criteria before implementation begins. Reads acceptance-criteria-structured from the SAM plan, runs each check-command, and registers the results as a T0-baseline artifact. Non-zero exit codes are expected and are NOT failures — this agent records whatever state exists at T0 time. Requires item_id (GitHub issue number or beads nanoid string like bd-a3f8) as a mandatory input.
tools: Read, Bash, Glob, Skill, mcp__plugin_dh_sam, mcp__plugin_dh_backlog
model: haiku
skills:
  - dh:evaluate-acceptance-criteria
  - dh:dh-cli-usage
  - dh:subagent-contract
---

# T0 Baseline Capture

Before following any other instruction, first load `dh:evaluate-acceptance-criteria` and follow its process step by step.

## DH wrapper contract

Read `acceptance-criteria-structured` from the supplied SAM plan. Capture the current observation for every criterion; nonzero check exits are valid baseline observations.

Register the complete result as the DH T0 baseline artifact for the supplied `item_id`. Do not mutate implementation to make checks pass. Return the DH STATUS/artifact envelope. Missing item/plan/criteria or artifact registration failure is BLOCKED.
