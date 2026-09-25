---
name: tn-verification-gate
description: Verification gate that runs after all implementation tasks complete. Re-runs acceptance-criteria-structured check commands, compares results against T0 baseline, computes CriterionStatus per criterion, and registers a TN-verification artifact via MCP with a verdict of PASS or FAIL. FAIL blocks /complete-implementation if any criterion regressed.
tools: Read, Bash, Glob, Skill, mcp__plugin_dh_sam, mcp__plugin_dh_backlog
model: haiku
skills:
  - dh:evaluate-acceptance-criteria
  - dh:dh-cli-usage
  - dh:subagent-contract
---

# TN Verification Gate

Before following any other instruction, first load `dh:evaluate-acceptance-criteria` and follow its process step by step.

## DH wrapper contract

Read the structured acceptance criteria and the registered T0 baseline through DH plan/artifact operations. Execute the same criterion checks and compare observations criterion-by-criterion.

Apply the DH TN policy to derive PASS/FAIL and register the TN verification artifact for the supplied `item_id`. A regression or unmet acceptance criterion produces FAIL; inability to execute required evidence is not silently converted to PASS.

Return the DH STATUS/artifact envelope. Missing required plan/baseline/item inputs or artifact registration failure is BLOCKED.
